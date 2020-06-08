from cffi import FFI


def main():
    ffi = FFI()

    # declare functions to export
    ffi.cdef(
        """
        char* fetchHelmChart(char* p0, char* p1, char* p2, char* p3);
        void free(void* ptr);
    """
    )

    ffi.set_source("helm_fetch_binding", None)  # specify name for importing this module

    ffi.compile(verbose=True)


if __name__ == "__main__":
    main()
