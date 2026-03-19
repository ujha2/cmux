from cmux.tasks.models import OutputFormat, SkillDef

definition = SkillDef(
    name="deck",
    description="Make a presentation deck",
    prompt_template=(
        "Create a presentation deck for:\n\n{{task}}\n\n"
        "Guidelines:\n"
        "- Max 5 bullet points per slide\n"
        "- Use clear, concise language\n"
        "- Include a title slide, agenda, key content slides, and summary\n"
        "- Suggest data visualizations where appropriate\n"
        "- End with clear next steps / call to action\n\n"
        "Output the content in a structured format with slide titles and bullet points."
    ),
    output_formats=[OutputFormat.PPTX],
    tools=["Read", "Write", "WebSearch"],
    template_files=["ppt_style.md"],
    time_estimate_manual_minutes=120,
    aliases=["presentation", "pptx", "slides", "powerpoint"],
    keywords=["deck", "presentation", "slides", "powerpoint", "pitch"],
)
