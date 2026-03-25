from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_db
from app.models import Market, Opportunity, Relation
from app.schemas import MarketRead, OpportunityDetail, OpportunityListItem, OpportunityType, RefreshResponse
from app.services.refresh_pipeline import RefreshPipeline


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/markets", response_model=list[MarketRead])
def list_markets(db: Session = Depends(get_db)) -> list[Market]:
    stmt = select(Market).order_by(Market.fetched_at.desc(), Market.id.desc())
    return list(db.scalars(stmt))


@router.get("/markets/{market_id}", response_model=MarketRead)
def get_market(market_id: int, db: Session = Depends(get_db)) -> Market:
    market = db.get(Market, market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="Market not found")
    return market


@router.get("/opportunities", response_model=list[OpportunityListItem])
def list_opportunities(
    opportunity_type: OpportunityType | None = Query(default=None),
    sort: str = Query(default="score_desc"),
    db: Session = Depends(get_db),
) -> list[OpportunityListItem]:
    stmt = (
        select(Opportunity)
        .options(joinedload(Opportunity.relation).joinedload(Relation.market_a))
        .options(joinedload(Opportunity.relation).joinedload(Relation.market_b))
        .where(Opportunity.active.is_(True))
    )
    if opportunity_type is not None:
        stmt = stmt.where(Opportunity.opportunity_type == opportunity_type.value)
    if sort == "score_asc":
        stmt = stmt.order_by(Opportunity.score.asc(), Opportunity.id.asc())
    else:
        stmt = stmt.order_by(Opportunity.score.desc(), Opportunity.id.desc())

    opportunities = db.scalars(stmt).unique().all()
    return [
        OpportunityListItem(
            opportunity=opportunity,
            relation=opportunity.relation,
            market_a=opportunity.relation.market_a,
            market_b=opportunity.relation.market_b,
        )
        for opportunity in opportunities
    ]


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetail)
def get_opportunity(opportunity_id: int, db: Session = Depends(get_db)) -> OpportunityDetail:
    stmt = (
        select(Opportunity)
        .options(joinedload(Opportunity.relation).joinedload(Relation.market_a))
        .options(joinedload(Opportunity.relation).joinedload(Relation.market_b))
        .where(Opportunity.id == opportunity_id)
    )
    opportunity = db.scalars(stmt).unique().first()
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return OpportunityDetail(
        opportunity=opportunity,
        relation=opportunity.relation,
        market_a=opportunity.relation.market_a,
        market_b=opportunity.relation.market_b,
    )


@router.post("/admin/refresh", response_model=RefreshResponse)
def refresh(db: Session = Depends(get_db)) -> RefreshResponse:
    pipeline = RefreshPipeline(db)
    return pipeline.run()
