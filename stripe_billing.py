import os
import stripe
from fastapi import APIRouter, HTTPException, Request, Header

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_...")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_...")

router = APIRouter()

@router.post("/api/v1/billing/checkout")
async def crear_sesion_pago(empresa_id: str, price_id: str):
    """
    Genera la URL de la pasarela segura de Stripe para que el cliente pague.
    """
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,  # ID del plan creado en el Dashboard de Stripe
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://boutiquelegaltransporte.es/dashboard?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://boutiquelegaltransporte.es/precios',
            client_reference_id=empresa_id,
        )
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/v1/billing/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Escucha eventos de Stripe para activar o suspender la cuenta del cliente según su pago.
    """
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, endpoint_secret
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error Webhook: {str(e)}")

    # Manejo de pago de suscripción completado
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        empresa_id = session.get('client_reference_id')
        
        # Lógica en BD: Marcar la empresa como ACTIVA y actualizar su cupo de DeCA
        print(f"Suscripción activada con éxito para la empresa: {empresa_id}")

    # Manejo de fallo de cobro
    elif event['type'] == 'invoice.payment_failed':
        session = event['data']['object']
        # Lógica en BD: Enviar aviso de pago fallido o suspender la emisión de DeCA
        print("Fallo en el cobro recurrente")

    return {"status": "success"}