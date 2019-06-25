from cffi import FFI


def main():
    ffi = FFI()

    # declare functions to export
    ffi.cdef("""
        int renderChart(char* p0, char* p1);
    """)

    ffi.set_source(
        "_template", # specify name for importing this module
        None
    )

    ffi.compile(verbose=True)


if __name__ == '__main__':
    main()
