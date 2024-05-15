{* SHOULD BE PLACED IN $HOME/.virtualenvs/somadata/share/jupyter/nbconvert/templates/pythoncodeblocks.tpl *}
{% extends 'markdown.tpl' %}
{% block stream %}
*Output*
``` python
{{ output.text | comment_lines(prefix="#> ") }}
```
{% endblock stream %}


{% block data_text scoped %}
*Output*
``` python
{{ output.data['text/plain'] | comment_lines(prefix="#> ")}}
```
{% endblock data_text %}


{% block data_html scoped %}
*Output*
{{ output.data['text/html'] }}
{% endblock data_html %}