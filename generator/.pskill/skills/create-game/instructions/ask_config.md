{% if steps.setup.json.findings is defined %}The setup could not use a config:
{% for finding in steps.setup.json.findings %}- {{ finding.message }}{% if finding.path is defined %} (field `{{ finding.path }}`){% endif %}
{% endfor %}{% else %}{{ steps.setup.json.message | default('The setup could not read the config.') }}
{% endif %}
Ask the user for the full path of their `.mystery-config.json` file. Tell them that they can make one by opening `configurator/index.html` in this repository with a double-click, and saving it from there. They can also answer `defaults` to generate a game with the default settings.

Your answer: the path that the user gives, or the word `defaults`.
