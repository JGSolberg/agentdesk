from agentdesk_api.bootstrap import ROADMAP, bootstrap
from agentdesk_api.database import SessionLocal
from agentdesk_api.models import Project, TicketStatus


def test_bootstrap_creates_agentdesk_roadmap_once() -> None:
    with SessionLocal() as db:
        project, created = bootstrap(db)
        assert project.name == "AgentDesk"
        assert created == len(ROADMAP) + 10

        tickets = list(project.tickets)
        assert len(tickets) == len(ROADMAP) + 10
        assert any(ticket.title == "AD-7 Ticket detail view" and ticket.status == TicketStatus.IN_PROGRESS for ticket in tickets)
        assert any(ticket.title == "AD-8 Event model" and ticket.status == TicketStatus.BACKLOG for ticket in tickets)

        same_project, created_again = bootstrap(db)
        assert same_project.id == project.id
        assert created_again == 0
        assert len(same_project.tickets) == len(ROADMAP) + 10
        assert db.query(Project).filter(Project.name == "AgentDesk").count() == 1
