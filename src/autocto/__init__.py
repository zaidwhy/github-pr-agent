"""AutoCTO - the engineering-manager layer of the GitHub PR Agent.

AutoCTO understands a repository, reports on its health, triages its issues, and drafts a
pull-request plan. It deliberately stops short of writing the code: on the free/local model
the ecosystem uses, analysis and planning are reliable while code generation is not. The
actual implementation is done by the `/github-pr` Claude Code skill, which consumes the plan
AutoCTO produces.
"""

__version__ = "0.1.0"
