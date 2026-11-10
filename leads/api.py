"""HTTP endpoints for leads. The website's forms post here.

Run locally:  uvicorn leads.api:app --reload
"""
import logging

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import ValidationError

from leads.dnc import DncList
from leads.models import InboundLead, WaitlistSignup
from leads.store import LeadStore
from shared.config import get_settings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/leads", tags=["leads"])


def get_db_dep():
    from shared.db import get_db
    return get_db()


async def read_body(request: Request) -> tuple[dict, bool]:
    """The site sends JSON; if JavaScript is off the browser sends a normal form instead. Accept both."""
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            data = await request.json()
        except ValueError:
            data = None
        return (data if isinstance(data, dict) else {}), False
    form = await request.form()
    return {k: v for k, v in form.items() if isinstance(v, str)}, True


def done(is_form: bool, path: str):
    """JSON for the site's JavaScript; a redirect back to the site for plain form posts."""
    if is_form:
        return RedirectResponse(f"{get_settings().SITE_URL.rstrip('/')}{path}?sent=1", status_code=303)
    return {"ok": True}


def invalid(e: ValidationError):
    fields = sorted({str(err["loc"][0]) for err in e.errors() if err["loc"]})
    return JSONResponse({"ok": False, "error": "invalid_fields", "fields": fields}, status_code=422)


@router.post("/inbound")
async def inbound(request: Request, db=Depends(get_db_dep)):
    """Free website preview form → a new lead with source 'inbound'. Free: no approval needed."""
    data, is_form = await read_body(request)
    try:
        lead = InboundLead(**data)
    except ValidationError as e:
        return invalid(e)
    if lead.website:  # spam trap filled in: pretend it worked, save nothing
        return done(is_form, "/preview")
    if DncList.load(db).blocks(phone=lead.phone, email=lead.email):
        # Respect the do-not-contact list. We still reply "ok" so the list isn't revealed.
        log.info("Inbound lead matched do-not-contact list; not saved")
        return done(is_form, "/preview")
    LeadStore(db).save_inbound(lead)
    return done(is_form, "/preview")


@router.post("/waitlist")
async def waitlist(request: Request, db=Depends(get_db_dep)):
    """Founders waitlist form."""
    data, is_form = await read_body(request)
    try:
        signup = WaitlistSignup(**data)
    except ValidationError as e:
        return invalid(e)
    if not signup.website:
        LeadStore(db).save_waitlist(signup)
    return done(is_form, "/founders")


def create_app() -> FastAPI:
    app = FastAPI(title="Prezence API")
    # CORS: lets the website (a different domain) call this API from the browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()
