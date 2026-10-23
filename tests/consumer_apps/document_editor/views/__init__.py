def editor(params):
    return """
<section id="editor-host">
  <div id="editor" contenteditable="true">selectable text</div>
  <div class="textLayer"><span>PDF selectable layer</span></div>
  <canvas id="pdf-canvas"></canvas>
</section>
"""


def register_routes(router):
    router.add("/editor", editor, name="editor", title="Editor", layout="blank")
