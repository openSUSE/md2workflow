from setuptools import setup, find_packages


setup(
    name="md2workflow",
    description="Create a JIRA or other Workflow from markdown files.",
    long_description="Create a JIRA or other Workflow from markdown files.",
    version="1.3",
    license="GPLv3",
    author="Lubos Kocman",
    author_email="Lubos.Kocman@suse.com",
    packages=["md2workflow", "md2workflow.backend", "md2workflow.validation", ],
    package_data={"md2workflow": ["example/release-checklist/*"]},
    url="https://github.com/lkocman/md2workflow.git",
    py_modules=find_packages(),

    data_files=[
        ("config", [
			"config/local.conf",
			"config/jira-example.conf"
	]),
        ("example", [
                        "example/project_config.md",
                        "example/alpha.md",
                        "example/beta.md",
                        "example/ga.md",
                        "example/my_project.conf",
                        "example/rc.md",
                        "example/repetitiveTasksForMilestones.md"
       ]),
    ],
    setup_requires=["pytest-runner",],
    tests_require=["pytest",],
    install_requires=["jira",],
    entry_points = {
	"console_scripts": [
    	"md2workflow = md2workflow.cli:main",
        ],
    },
    classifiers = [
        "Topic :: Text Processing :: Markup",
    ]
)
