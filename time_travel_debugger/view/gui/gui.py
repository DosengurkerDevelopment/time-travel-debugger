from debuggingbook.bookutils import HTML
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

here = os.path.dirname(__file__)
templates = os.path.abspath(os.path.join(here, '../../../templates'))

env = Environment(
    loader=FileSystemLoader(templates),
    autoescape=select_autoescape(["html"]),
)

example_code = """
def hello(name):
    name += "!"
    print("Hello" + name)
"""


class GUI(object):
    def __init__(self):
        pass

    def execute(self):
        pass

    def update(self, state, draw_update):
        template = env.get_template("debugger.j2")
        render = template.render(codelines=example_code.split("\n"))
        print(render)
        print("penis")
        return HTML(render)


def slider(rec):
    lines_over_time = [line for (line, var) in rec]
    vars_over_time = []
    for (line, vars) in rec:
        vars_over_time.append(", ".join(f"{var} = {repr(vars[var])}" for var in vars))

    # print(lines_over_time)
    # print(vars_over_time)

    template = f"""
    <div class="time_travel_debugger">
      <input type="range" min="0" max="{len(lines_over_time) - 1}"
      value="0" class="slider" id="time_slider">
      Line <span id="line">{lines_over_time[0]}</span>:
      <span id="vars">{vars_over_time[0]}</span>
    </div>
    <script>
       var lines_over_time = {lines_over_time};
       var vars_over_time = {vars_over_time};

       var time_slider = document.getElementById("time_slider");
       var line = document.getElementById("line");
       var vars = document.getElementById("vars");

       time_slider.oninput = function() {{
          line.innerHTML = lines_over_time[this.value];
          vars.innerHTML = vars_over_time[this.value];
       }}
    </script>
    """
    # print(template)
    return HTML(template)
