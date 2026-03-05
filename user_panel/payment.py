import os
import stripe
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from django.utils import timezone as djtz
from datetime import timedelta

from .django_setup import setup as django_setup
django_setup()

from lms.models import LMSUser, Course, Plan, Subscription, Payment, Enrollment, Progress, ActivityLog, Notification  # noqa: E402
from .deps import get_current_user  # noqa: E402
from asgiref.sync import sync_to_async  # noqa: E402

router = APIRouter(tags=["Payments - Stripe"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_...")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_...")
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:8000")

class CheckoutRequest(BaseModel):
    type: str  # 'course' or 'plan'
    item_id: int

@router.post("/create-checkout-session/")
def create_checkout_session(req: CheckoutRequest, user: LMSUser = Depends(get_current_user)):
    try:
        if req.type == "course":
            item = Course.objects.get(pk=req.item_id, status="published")
            amount = int(item.price * 100)  # Convert to cents
            name = item.title
            metadata = {"type": "course", "item_id": item.id, "user_id": user.id}
        elif req.type == "plan":
            item = Plan.objects.get(pk=req.item_id)
            amount = int(item.price * 100)
            name = item.name
            metadata = {"type": "plan", "item_id": item.id, "user_id": user.id}
        else:
            raise HTTPException(status_code=400, detail="Invalid item type")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {"name": name},
                    "unit_amount": amount,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{OAUTH_REDIRECT_BASE}/payment/success/",
            cancel_url=f"{OAUTH_REDIRECT_BASE}/payment/cancel/",
            client_reference_id=str(user.id),
            metadata=metadata
        )
        return {"url": session.url}

    except Course.DoesNotExist:
        raise HTTPException(status_code=404, detail="Course not found")
    except Plan.DoesNotExist:
        raise HTTPException(status_code=404, detail="Plan not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@sync_to_async
def fulfill_order(item_type: str, item_id: int, user_id: int, transaction_id: str):
    user = LMSUser.objects.get(pk=user_id)
    
    if item_type == "plan":
        plan = Plan.objects.get(pk=item_id)
        start = djtz.now()
        end = start + timedelta(days=plan.duration_days)
        # Create Subscription
        Subscription.objects.create(user=user, plan=plan, start_date=start, end_date=end, status="active")
        # Create Payment record
        Payment.objects.create(
            user=user, plan=plan, amount=plan.price, 
            stripe_transaction_id=transaction_id, status="completed"
        )
        # Notify
        Notification.objects.create(user=user, message=f"Subscribed to {plan.name}")
        ActivityLog.objects.create(user=user, action_type="subscribe", action_detail=f"Bought {plan.name}")

    elif item_type == "course":
        course = Course.objects.get(pk=item_id)
        # Create Enrollment
        obj, created = Enrollment.objects.get_or_create(user=user, course=course)
        if created:
            Progress.objects.create(enrollment=obj, completed_lessons=0, progress_percent=0.0)
            ActivityLog.objects.create(user=user, action_type="enroll", action_detail=f"Bought {course.title}")
            Notification.objects.create(user=user, message=f"You enrolled in {course.title}")
        # Create Payment record
        Payment.objects.create(
            user=user, course=course, amount=course.price, 
            stripe_transaction_id=transaction_id, status="completed"
        )


@router.post("/webhook")
@router.post("/webhook/")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # Only fulfill if payment is successful
        if session.get("payment_status") == "paid":
            metadata = session.get("metadata", {})
            item_type = metadata.get("type")
            item_id = int(metadata.get("item_id", 0))
            user_id = int(metadata.get("user_id", 0))
            transaction_id = session.get("payment_intent") or session.get("id")

            try:
                await fulfill_order(item_type, item_id, user_id, transaction_id)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Webhook Fulfillment Error: {e}")
                raise HTTPException(status_code=500, detail="Error fulfilling order")

    return {"status": "success"}
