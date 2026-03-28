# Marshmello

Online Music Streaming platform.

## Project Structure

```text
marshmello/
|-- .env.example
|-- .gitignore
|-- .python-version
|-- .replit
|-- .vscode/
|   \-- settings.json
|-- build.sh
|-- card.json
|-- cardupdate.py
|-- DEPLOYMENT.md
|-- main/
|   |-- __init__.py
|   |-- admin.py
|   |-- migrations/
|   |   |-- __init__.py
|   |   \-- 0001_initial.py
|   |-- models.py
|   |-- urls.py
|   \-- views.py
|-- manage.py
|-- Procfile
|-- README.md
|-- render.yaml
|-- requirements.txt
|-- runtime.txt
|-- static/
|   |-- admin/
|   |   |-- css/
|   |   |   |-- autocomplete.css
|   |   |   |-- base.css
|   |   |   |-- changelists.css
|   |   |   |-- dashboard.css
|   |   |   |-- fonts.css
|   |   |   |-- forms.css
|   |   |   |-- login.css
|   |   |   |-- responsive.css
|   |   |   |-- responsive_rtl.css
|   |   |   |-- rtl.css
|   |   |   |-- vendor/
|   |   |   |   \-- select2/
|   |   |   |       |-- LICENSE-SELECT2.md
|   |   |   |       |-- select2.css
|   |   |   |       \-- select2.min.css
|   |   |   \-- widgets.css
|   |   |-- fonts/
|   |   |   |-- LICENSE.txt
|   |   |   |-- README.txt
|   |   |   |-- Roboto-Bold-webfont.woff
|   |   |   |-- Roboto-Light-webfont.woff
|   |   |   \-- Roboto-Regular-webfont.woff
|   |   |-- img/
|   |   |   |-- calendar-icons.svg
|   |   |   |-- gis/
|   |   |   |   |-- move_vertex_off.svg
|   |   |   |   \-- move_vertex_on.svg
|   |   |   |-- icon-addlink.svg
|   |   |   |-- icon-alert.svg
|   |   |   |-- icon-calendar.svg
|   |   |   |-- icon-changelink.svg
|   |   |   |-- icon-clock.svg
|   |   |   |-- icon-deletelink.svg
|   |   |   |-- icon-no.svg
|   |   |   |-- icon-unknown.svg
|   |   |   |-- icon-unknown-alt.svg
|   |   |   |-- icon-viewlink.svg
|   |   |   |-- icon-yes.svg
|   |   |   |-- inline-delete.svg
|   |   |   |-- LICENSE
|   |   |   |-- README.txt
|   |   |   |-- search.svg
|   |   |   |-- selector-icons.svg
|   |   |   |-- sorting-icons.svg
|   |   |   |-- tooltag-add.svg
|   |   |   \-- tooltag-arrowright.svg
|   |   \-- js/
|   |       |-- actions.js
|   |       |-- actions.min.js
|   |       |-- admin/
|   |       |   |-- DateTimeShortcuts.js
|   |       |   \-- RelatedObjectLookups.js
|   |       |-- autocomplete.js
|   |       |-- calendar.js
|   |       |-- cancel.js
|   |       |-- change_form.js
|   |       |-- collapse.js
|   |       |-- collapse.min.js
|   |       |-- core.js
|   |       |-- inlines.js
|   |       |-- inlines.min.js
|   |       |-- jquery.init.js
|   |       |-- popup_response.js
|   |       |-- prepopulate.js
|   |       |-- prepopulate.min.js
|   |       |-- prepopulate_init.js
|   |       |-- SelectBox.js
|   |       |-- SelectFilter2.js
|   |       |-- urlify.js
|   |       \-- vendor/
|   |           |-- jquery/
|   |           |   |-- jquery.js
|   |           |   |-- jquery.min.js
|   |           |   \-- LICENSE.txt
|   |           |-- select2/
|   |           |   |-- i18n/
|   |           |   |   |-- af.js
|   |           |   |   |-- ar.js
|   |           |   |   |-- az.js
|   |           |   |   |-- bg.js
|   |           |   |   |-- bn.js
|   |           |   |   |-- bs.js
|   |           |   |   |-- ca.js
|   |           |   |   |-- cs.js
|   |           |   |   |-- da.js
|   |           |   |   |-- de.js
|   |           |   |   |-- dsb.js
|   |           |   |   |-- el.js
|   |           |   |   |-- en.js
|   |           |   |   |-- es.js
|   |           |   |   |-- et.js
|   |           |   |   |-- eu.js
|   |           |   |   |-- fa.js
|   |           |   |   |-- fi.js
|   |           |   |   |-- fr.js
|   |           |   |   |-- gl.js
|   |           |   |   |-- he.js
|   |           |   |   |-- hi.js
|   |           |   |   |-- hr.js
|   |           |   |   |-- hsb.js
|   |           |   |   |-- hu.js
|   |           |   |   |-- hy.js
|   |           |   |   |-- id.js
|   |           |   |   |-- is.js
|   |           |   |   |-- it.js
|   |           |   |   |-- ja.js
|   |           |   |   |-- ka.js
|   |           |   |   |-- km.js
|   |           |   |   |-- ko.js
|   |           |   |   |-- lt.js
|   |           |   |   |-- lv.js
|   |           |   |   |-- mk.js
|   |           |   |   |-- ms.js
|   |           |   |   |-- nb.js
|   |           |   |   |-- ne.js
|   |           |   |   |-- nl.js
|   |           |   |   |-- pl.js
|   |           |   |   |-- ps.js
|   |           |   |   |-- pt.js
|   |           |   |   |-- pt-BR.js
|   |           |   |   |-- ro.js
|   |           |   |   |-- ru.js
|   |           |   |   |-- sk.js
|   |           |   |   |-- sl.js
|   |           |   |   |-- sq.js
|   |           |   |   |-- sr.js
|   |           |   |   |-- sr-Cyrl.js
|   |           |   |   |-- sv.js
|   |           |   |   |-- th.js
|   |           |   |   |-- tk.js
|   |           |   |   |-- tr.js
|   |           |   |   |-- uk.js
|   |           |   |   |-- vi.js
|   |           |   |   |-- zh-CN.js
|   |           |   |   \-- zh-TW.js
|   |           |   |-- LICENSE.md
|   |           |   |-- select2.full.js
|   |           |   \-- select2.full.min.js
|   |           \-- xregexp/
|   |               |-- LICENSE.txt
|   |               |-- xregexp.js
|   |               \-- xregexp.min.js
|   |-- css/
|   |   |-- autocomplete.css
|   |   |-- base.css
|   |   |-- changelists.css
|   |   |-- dashboard.css
|   |   |-- fonts.css
|   |   |-- forms.css
|   |   |-- login.css
|   |   |-- responsive.css
|   |   |-- responsive_rtl.css
|   |   |-- rtl.css
|   |   |-- vendor/
|   |   |   \-- select2/
|   |   |       |-- LICENSE-SELECT2.md
|   |   |       |-- select2.css
|   |   |       \-- select2.min.css
|   |   \-- widgets.css
|   |-- fonts/
|   |   |-- LICENSE.txt
|   |   |-- README.txt
|   |   |-- Roboto-Bold-webfont.woff
|   |   |-- Roboto-Light-webfont.woff
|   |   \-- Roboto-Regular-webfont.woff
|   |-- formStyle.css
|   |-- heart.png
|   |-- hidden_heart.png
|   |-- img/
|   |   |-- calendar-icons.svg
|   |   |-- gis/
|   |   |   |-- move_vertex_off.svg
|   |   |   \-- move_vertex_on.svg
|   |   |-- icon-addlink.svg
|   |   |-- icon-alert.svg
|   |   |-- icon-calendar.svg
|   |   |-- icon-changelink.svg
|   |   |-- icon-clock.svg
|   |   |-- icon-deletelink.svg
|   |   |-- icon-no.svg
|   |   |-- icon-unknown.svg
|   |   |-- icon-unknown-alt.svg
|   |   |-- icon-viewlink.svg
|   |   |-- icon-yes.svg
|   |   |-- inline-delete.svg
|   |   |-- LICENSE
|   |   |-- README.txt
|   |   |-- search.svg
|   |   |-- selector-icons.svg
|   |   |-- sorting-icons.svg
|   |   |-- tooltag-add.svg
|   |   \-- tooltag-arrowright.svg
|   |-- marshmello_favicon.png
|   |-- pause.png
|   |-- play.png
|   |-- player.css
|   |-- playlist.css
|   |-- search.css
|   |-- skip-back.svg
|   |-- skip-forward.svg
|   |-- vol-0.svg
|   |-- vol-1.svg
|   |-- vol-2.svg
|   \-- vol-3.svg
|-- templates/
|   |-- login.html
|   |-- player.html
|   |-- playlist.html
|   |-- search.html
|   \-- signup.html
|-- vercel.json
\-- youtify/
	|-- __init__.py
	|-- asgi.py
	|-- settings.py
	|-- urls.py
	\-- wsgi.py
```
