from agentdesk_api.bootstrap import ROADMAP, bootstrap
from agentdesk_api.database import SessionLocal
from agentdesk_api.models import Project, TicketStatus


def test_bootstrap_creates_and_enriches_agentdesk_roadmap_idempotently() -> None:
    with SessionLocal() as db:
        project, created = bootstrap(db)
        assert project.name == "AgentDesk"
        assert created == len(ROADMAP) + 10

        tickets = list(project.tickets)
        assert len(tickets) == len(ROADMAP) + 10

        detail = next(ticket for ticket in tickets if ticket.title == "AD-7 Ticket detail and editing")
        assert detail.status == TicketStatus.IN_PROGRESS
        assert detail.goal
        assert detail.description
        assert len(detail.acceptance_criteria) >= 3
        assert detail.definition_of_done
        assert detail.relevant_files
        assert detail.estimated_complexity == "medium"

        repository_registration = next(ticket for ticket in tickets if ticket.title == "AD-10 Repository registration")
        assert repository_registration.status == TicketStatus.BACKLOG
        assert "Repositories can be added, listed, edited, and removed" in repository_registration.acceptance_criteria
        assert repository_registration.relevant_files

        same_project, created_again = bootstrap(db)
        assert same_project.id == project.id
        assert created_again == 0
        assert len(same_project.tickets) == len(ROADMAP) + 10
        assert db.query(Project).filter(Project.name == "AgentDesk").count() == 1
