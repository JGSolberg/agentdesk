from agentdesk_api.bootstrap import ROADMAP, bootstrap
from agentdesk_api.database import SessionLocal
from agentdesk_api.models import TicketType
from agentdesk_api.roadmap_epics import enrich_roadmap_epics
from agentdesk_api.roadmap_identity import repair_roadmap_identity


def test_roadmap_epics_are_enriched_idempotently() -> None:
    with SessionLocal() as db:
        project, _ = bootstrap(db)
        repair_roadmap_identity(db)

        updated = enrich_roadmap_epics(db)
        assert updated == 10

        tickets = list(project.tickets)
        event_ledger = next(ticket for ticket in tickets if ticket.type == TicketType.EPIC and ticket.title == "Milestone 3 — Event ledger")
        children = [item for item in ROADMAP if item.milestone == 3]

        assert event_ledger.ticket_key == "AD-30"
        assert event_ledger.goal
        assert event_ledger.description
        assert len(event_ledger.acceptance_criteria) == len(children)
        assert event_ledger.definition_of_done
        assert event_ledger.constraints
        assert event_ledger.context
        assert event_ledger.relevant_files
        assert event_ledger.estimated_complexity == "epic"

        assert enrich_roadmap_epics(db) == 0
