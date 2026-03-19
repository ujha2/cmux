from cmux.tasks.models import OutputFormat, SkillDef

definition = SkillDef(
    name="prototype",
    description="Generate a working prototype (HTML/React/etc)",
    prompt_template=(
        "Build a working prototype for:\n\n{{task}}\n\n"
        "Requirements:\n"
        "- Create a functional, interactive prototype\n"
        "- Use appropriate technology (HTML/CSS/JS, React, or similar)\n"
        "- Focus on the core user flow\n"
        "- Include basic styling for presentability\n"
        "- Add placeholder data that feels realistic\n"
        "- Make it easy to demo\n\n"
        "Output all code files needed to run the prototype."
    ),
    output_formats=[OutputFormat.CODE],
    tools=["Read", "Write", "Bash", "Glob"],
    template_files=[],
    time_estimate_manual_minutes=240,
    aliases=["proto", "mockup", "demo"],
    keywords=["prototype", "build", "create", "demo", "mockup", "interactive", "ui"],
)
