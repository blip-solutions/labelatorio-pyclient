def batchify(iterable, chunk_size):
    """
    creates chunks of size from itterable...

    For example: batch([1,2,3,4,5,6,7],3) -> [ [1,2,3], [4,5,6], [7] ]
    """
    l = len(iterable)
    for ndx in range(0, l, chunk_size):
        yield iterable[ndx:min(ndx + chunk_size, l)]
