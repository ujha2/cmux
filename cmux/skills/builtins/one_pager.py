from cmux.tasks.models import OutputFormat, SkillDef

definition = SkillDef(
    name="one_pager",
    description="Write a 1-pager for a feature or initiative",
    prompt_template=(
        "Write a concise 1-pager document for the following:\n\n{{task}}\n\n"
        "Structure:\n"
        "- Lead with the ask / recommendation\n"
        "- Problem statement (2-3 sentences)\n"
        "- Proposed solution (key details only)\n"
        "- Expected impact / ROI\n"
        "- Timeline and next steps\n\n"
        "Keep it to 1 page. Be direct and data-driven."
    ),
    output_formats=[OutputFormat.DOCX, OutputFormat.MARKDOWN],
    tools=["Read", "Write", "WebSearch"],
    template_files=["one_pager_format.md"],
    time_estimate_manual_minutes=90,
    aliases=["one-pager", "1-pager", "1pager"],
    keywords=["one pager", "brief", "executive summary", "initiative", "proposal"],
)
