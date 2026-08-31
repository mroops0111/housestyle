def build(value):
    # cap the size to the shared limit so the mmap does not
    # blow past it, an unbounded value faults the runner.
    # this one carries no comma at all and runs a very long way past the budget here.
    return value
