// this is the bridging C file just to test if so can be called properly from Python

#include <stdio.h>
//#include "template.h"
#include "template.h"

int main() {
//    char* m = "hello world from C!";
//    renderChart(m);
//    return 0;
    char* m = "helm_python/chart/acs-engine-autoscaler";
    int a = renderChart(m);
    printf("%d", a);
}