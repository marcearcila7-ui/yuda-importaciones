from pydantic import BaseModel


class VapidPublicKeyResponse(BaseModel):
    public_key: str


class PushSubscriptionInput(BaseModel):
    """Lo que devuelve pushManager.subscribe() en el navegador."""

    endpoint: str
    p256dh: str
    auth: str


class PushUnsubscribeInput(BaseModel):
    endpoint: str
