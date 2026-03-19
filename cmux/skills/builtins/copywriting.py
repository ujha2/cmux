from cmux.tasks.models import OutputFormat, SkillDef

definition = SkillDef(
    name="copywriting",
    description="Marketing copy, landing pages, messaging",
    prompt_template=(
        "Write marketing copy for:\n\n{{task}}\n\n"
        "Guidelines:\n"
        "- Clear, compelling headline\n"
        "- Focus on benefits, not just features\n"
        "- Use the target audience's language\n"
        "- Include a strong call to action\n"
        "- Provide multiple variants where helpful\n"
        "- Consider SEO if relevant\n\n"
        "Deliver polished, ready-to-use copy."
    ),
    output_formats=[OutputFormat.MARKDOWN],
    tools=["Read", "Write", "WebSearch"],
    template_files=["copy_voice.md"],
    time_estimate_manual_minutes=90,
    aliases=["copy", "marketing", "messaging", "landing_page"],
    keywords=["copy", "marketing", "landing page", "messaging", "headline", "tagline", "brand"],
)
