from glob import glob
from setuptools import setup, find_packages


setup(
    name="md2workflow",
    description="Create a JIRA or other Workflow from markdown files.",
    long_description="Create a JIRA or other Workflow from markdown files.",
    version="1.4.1",
    license="GPLv3",
    author="Lubos Kocman",
    author_email="Lubos.Kocman@suse.com",
    packages=["md2workflow", "md2workflow.backend", "md2workflow.validation", ],
    #package_data={"md2workflow": ["example/release-checklist/*"]},
    url="https://github.com/lkocman/md2workflow.git",
    py_modules=find_packages(),
    data_files=[('share/md2workflow/example', glob('example/*')), ('share/md2workflow/config', glob('config/*'))],
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
        "Topic :: Utilities",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    keywords=['SUSE', 'Workflow', 'JIRA', "Process", "Markdown", "Release Management"],
)
