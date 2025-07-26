"""
Message formatting utilities.

Formats project data into Telegram messages.
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Formats project data into user-friendly messages."""
    
    @staticmethod
    def clean_html_description(description: str) -> str:
        """Clean HTML from project description for Telegram compatibility."""
        if not description:
            return "Опис відсутній"
        
        # Replace common HTML breaks with newlines first
        description = description.replace("<p>", "").replace("</p>", "\n")
        description = description.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
        
        # Remove any remaining HTML tags
        description = re.sub(r'<[^>]+>', '', description)
        
        return description.strip()
    
    @staticmethod
    def format_budget(budget: Dict[str, Any]) -> str:
        """Format budget information."""
        if not budget or "amount" not in budget:
            return ""
        
        return f"{budget['amount']} {budget.get('currency', '')}"
    
    @staticmethod
    def format_skills(skills: list) -> str:
        """Format skills list."""
        if not skills:
            return ""
        
        return ", ".join([skill.get("name", "") for skill in skills])
    
    @staticmethod
    def get_skill_ids(skills: list) -> list:
        """Extract skill IDs from skills list."""
        return [str(skill.get("id")) for skill in skills if skill.get("id")]
    
    @staticmethod
    def format_employer_name(employer: Dict[str, Any]) -> str:
        """Format employer name with login."""
        if not employer:
            return ""
        
        first_name = employer.get('first_name', '')
        last_name = employer.get('last_name', '')
        login = employer.get('login', '')
        
        # Build name
        name = f"{first_name} {last_name}".strip()
        
        # Add login if available
        if login:
            if name:
                return f"{name} (@{login})"
            else:
                return f"@{login}"
        
        return name if name else ""
    
    @staticmethod
    def get_project_url(project: Dict[str, Any]) -> str:
        """Extract project URL from project data."""
        project_id = project.get("id")
        links = project.get("links", {})
        
        # Extract URL based on the actual API structure
        if isinstance(links, dict) and "self" in links:
            # Check if self is a dictionary with 'web' key (as per API example)
            if isinstance(links["self"], dict) and "web" in links["self"]:
                return links["self"]["web"]
            # Check if self is a direct string URL
            elif isinstance(links["self"], str):
                return links["self"]
        
        # Fallback to the constructed URL if we couldn't extract it
        return f"https://freelancehunt.com/project/{project_id}.html"
    
    @staticmethod
    def format_project_message(project: Dict[str, Any], show_skill_ids: bool = False) -> str:
        """Format project data into a Telegram message."""
        attributes = project.get("attributes", {})
        
        # Basic project info
        title = attributes.get("name", "Назва відсутня")
        description = MessageFormatter.clean_html_description(
            attributes.get("description_html", attributes.get("description", ""))
        )
        
        # Budget
        budget = attributes.get("budget", {})
        budget_text = MessageFormatter.format_budget(budget)
        
        # Skills
        skills = attributes.get("skills", [])
        skills_text = MessageFormatter.format_skills(skills)
        
        # Employer
        employer = attributes.get("employer", {})
        employer_name = MessageFormatter.format_employer_name(employer)
        
        # Project URL
        project_url = MessageFormatter.get_project_url(project)
        
        # Build message
        message_text = (
            f"<b>🔥 Новий проект:</b> {title}\n\n"
            f"<b>Опис:</b> {description[:200]}...\n\n"
        )
        
        if budget_text:
            message_text += f"<b>Бюджет:</b> {budget_text}\n"
        
        if skills_text:
            message_text += f"<b>Навички:</b> {skills_text}\n"
            
            # Add skill IDs for debugging if requested
            if show_skill_ids:
                skill_ids = MessageFormatter.get_skill_ids(skills)
                if skill_ids:
                    message_text += f"<b>ID навичок:</b> {', '.join(skill_ids)}\n"
        
        if employer_name:
            message_text += f"<b>Замовник:</b> {employer_name}\n"
        
        message_text += f"\n<b>🔗 <a href='{project_url}'>Відкрити проект</a></b>"
        
        return message_text


# Global message formatter instance
message_formatter = MessageFormatter()