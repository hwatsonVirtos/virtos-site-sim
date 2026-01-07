import matplotlib.pyplot as plt

def line_chart(title: str, y, x=None, ylabel: str = "", xlabel: str = "timestep"):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    if x is None:
        x = list(range(len(y)))
    ax.plot(x, y)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return fig
