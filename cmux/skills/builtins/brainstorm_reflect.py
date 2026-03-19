from cmux.tasks.models import OutputFormat, SkillDef

definition = SkillDef(
    name="brainstorm_reflect",
    description="Critical review to elevate quality of a doc",
    prompt_template=(
        "Critically review and improve the following:\n\n{{task}}\n\n"
        "Process:\n"
        "1. Read and understand the document's purpose\n"
        "2. Identify strengths and weaknesses\n"
        "3. Challenge assumptions and logic gaps\n"
        "4. Suggest specific improvements with rationale\n"
        "5. Propose alternative framings or angles\n"
        "6. Rate overall quality and readiness\n\n"
        "Output an annotated version with inline comments and a summary of suggestions."
    ),
    output_formats=[OutputFormat.MARKDOWN],
    tools=["Read", "Write"],
    template_files=[],
    time_estimate_manual_minutes=60,
    aliases=["review", "brainstorm", "reflect", "critique"],
    keywords=["review", "brainstorm", "reflect", "critique", "improve", "elevate", "feedback"],
)
