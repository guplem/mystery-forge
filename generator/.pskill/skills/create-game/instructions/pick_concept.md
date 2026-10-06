Show the user the three story concepts, with only their titles and teasers (no other detail from the files: the user may play this game):

{% for teaser in steps.concepts.results[0].teasers %}{{ loop.index }}. **{{ teaser.title }}**: {{ teaser.teaser }}
{% endfor %}
Ask which one they want. After this choice the run asks nothing more, so they can leave.
