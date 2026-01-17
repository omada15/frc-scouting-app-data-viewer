from bokeh.plotting import figure, show
from bokeh.io import curdoc
from bokeh.models import NumeralTickFormatter
import random
#sessions = ["auto", "transition", "phase 1", "phase 2", "phase 3", "phase 4", "endgame"]
#total_points = [23, 10, 40, 0, 43, 0, 37]
y= random.sample(range(0,100),7)
x= list(range(0,26))
#curdoc().theme = "dark_minimal"
colors = [f"#{255:02x}{int((value * 255) / 100):02x}{255:02x}" for value in y]
score_graph = figure(
    title="Scores", 
    x_axis_label="Sessions", 
    y_axis_label="Total Points",
)
score_graph.line(
    x, 
    y, 
    legend_label="Score per phase", 
    line_width=0.5,
)
score_graph.background_fill_color=(204, 255, 255)
score_graph.border_fill_color=(102, 204, 255)
score_graph.xgrid.grid_line_color="black"
score_graph.ygrid.grid_line_color="black"
score_graph.xaxis.axis_label_text_font_size = "20pt"
score_graph.yaxis.axis_label_text_font_size = "20pt"
score_graph.scatter(x, y, fill_color = colors,line_color = "blue", size=15)
show(score_graph)
#notation for log
#y_axis_type="log",
# y_range=[0.001, 10 ** 11],