def slider(rec):
    lines_over_time = [line for (line, var) in rec]
    vars_over_time = []
    for (line, vars) in rec:
        vars_over_time.append(", ".join(f"{var} = {repr(vars[var])}"
                                        for var in vars))

    # print(lines_over_time)
    # print(vars_over_time)

    template = f'''
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
    '''
    # print(template)
    return HTML(template)
