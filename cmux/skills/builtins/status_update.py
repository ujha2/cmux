from cmux.tasks.models import OutputFormat, SkillDef

definition = SkillDef(
    name="status_update",
    description="Weekly/monthly status update",
    prompt_template=(
        "Write a status update for:\n\n{{task}}\n\n"
        "Structure:\n"
        "- Wins / accomplishments this period\n"
        "- In progress / current focus\n"
        "- Blockers & risks\n"
        "- Upcoming next period\n"
        "- Asks / needs from leadership\n\n"
        "Keep it concise, use bullet points, lead with impact."
    ),
    output_formats=[OutputFormat.MARKDOWN, OutputFormat.EMAIL],
    tools=["Read", "Write"],
    template_files=["weekly_status.md"],
    time_estimate_manual_minutes=45,
    aliases=["status", "weekly", "monthly_update"],
    keywords=["status", "update", "weekly", "monthly", "report", "progress"],
)
