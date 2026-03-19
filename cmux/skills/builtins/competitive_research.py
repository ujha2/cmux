from cmux.tasks.models import OutputFormat, SkillDef

definition = SkillDef(
    name="competitive_research",
    description="Research competitors, produce comparison",
    prompt_template=(
        "Conduct competitive research for:\n\n{{task}}\n\n"
        "Deliverable:\n"
        "- Executive summary of competitive landscape\n"
        "- Competitor profiles (key players)\n"
        "- Feature comparison matrix\n"
        "- Pricing comparison (if applicable)\n"
        "- Strengths/weaknesses analysis\n"
        "- Strategic recommendations\n"
        "- Sources and references\n\n"
        "Be thorough but focus on actionable insights."
    ),
    output_formats=[OutputFormat.MARKDOWN],
    tools=["Read", "Write", "WebSearch", "WebFetch"],
    template_files=[],
    time_estimate_manual_minutes=150,
    aliases=["comp_research", "competitive", "competitor_analysis"],
    keywords=["competitor", "competitive", "research", "comparison", "landscape", "market"],
)
