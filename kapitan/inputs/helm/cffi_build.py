from cffi import FFI


def main():
    ffi = FFI()

    # declare functions to export
    ffi.cdef("""
        char* renderChart(char* p0, char* p1, char* p2, char* p3, char* p4, char* p5);
        void free(void* ptr);
    """)

    ffi.set_source(
        "helm_binding",  # specify name for importing this module
        None
    )

    ffi.compile(verbose=True)


if __name__ == '__main__':
    main()
