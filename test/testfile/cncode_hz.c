/*
 * ~{ND<~C{~}: random_chinese_sample.c
 * ~{9&D\ChJv~}: ~{UbJGR;8vQ]J>VPNDW"JM5D~}C~{SoQT4zBkJ>@}~}
 * ~{W"Rb~}: ~{4K4zBk=vSCSZ1`Bk2bJT#,2;1#V$9&D\MjU{PT~}
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ~{6(ReR;P)3#A?~}
#define ~{Wn4sV5~} 100
#define ~{;:3eGx4sP!~} 256

// ~{=a99Le6(Re~}
typedef struct ~{Q'IzPEO"~} {
    int ~{Q':E~};
    char ~{PUC{~}[50];
    float ~{3I<(~};
} ~{Q'Iz~};

/*
 * ~{:/J}~}: ~{<FKcF=>y7V~}
 * ~{2NJ}~}: ~{3I<(J}Wi:MJ}A?~}
 * ~{75;X~}: ~{F=>y7VJ}V5~}
 * ~{K5Cw~}: ~{Ub@o0|:,AKR;P)VPNDWV7{SCSZ2bJT8wVV1`Bk~}
 */
float ~{<FKcF=>y7V~}(float ~{7VJ}~}[], int ~{J}A?~}) {
    float ~{W\7V~} = 0.0;
    int i;

    // ~{1i@zKySP7VJ}2"@[<S~}
    for (i = 0; i < ~{J}A?~}; i++) {
        ~{W\7V~} += ~{7VJ}~}[i];  // ~{@[<SC?8vQ'Iz5D7VJ}~}
    }

    // ~{75;XF=>yV5#,W"Rb4&@m3}AcGi?v~}
    return ~{J}A?~} > 0 ? ~{W\7V~} / ~{J}A?~} : 0;
}

/**
 * ~{Vw:/J}~} - ~{3LPrHk?Z5c~}
 * ~{0|:,6`VVVPNDWV7{:M7{:E#:!>!?!"#;#:~}''""~{#,!##?#!#(#)~}
 */
int main() {
    // ~{IyCw1dA?~}
    int i, ~{Q'IzJ}A?~} = 3;
    float ~{KySP7VJ}~}[~{Wn4sV5~}];
    char ~{AYJ1;:3eGx~}[~{;:3eGx4sP!~}];
    ~{Q'Iz~} ~{0`<6~}[10];  // ~{0`<6Q'IzJ}Wi~}

    printf("~{UbJGR;8v2bJT3LPr#,0|:,VPNDW"JM:M1dA?C{~}\n");

    /* ~{3uJ<;/Q'IzPEO"~} */
    ~{0`<6~}[0].~{Q':E~} = 1001;
    strcpy(~{0`<6~}[0].~{PUC{~}, "~{UEH}~}");  // ~{84VFPUC{~}
    ~{0`<6~}[0].~{3I<(~} = 85.5;

    ~{0`<6~}[1].~{Q':E~} = 1002;
    strcpy(~{0`<6~}[1].~{PUC{~}, "~{@nKD~}");  // ~{AmR;8vQ'Iz~}
    ~{0`<6~}[1].~{3I<(~} = 92.0;

    ~{0`<6~}[2].~{Q':E~} = 1003;
    strcpy(~{0`<6~}[2].~{PUC{~}, "~{MuNe~}");  // ~{5ZH}8vQ'Iz~}
    ~{0`<6~}[2].~{3I<(~} = 78.5;

    // ~{JU</KySP7VJ}SCSZ<FKc~}
    for (i = 0; i < ~{Q'IzJ}A?~}; i++) {
        ~{KySP7VJ}~}[i] = ~{0`<6~}[i].~{3I<(~};

        // ~{Jd3vC?8vQ'Iz5DPEO"~}
        printf("~{Q':E#:~}%d~{#,PUC{#:~}%s~{#,3I<(#:~}%.1f\n",
               ~{0`<6~}[i].~{Q':E~}, ~{0`<6~}[i].~{PUC{~}, ~{0`<6~}[i].~{3I<(~});
    }

    // ~{<FKc2"OTJ>F=>y7V~}
    float ~{F=>y7V~} = ~{<FKcF=>y7V~}(~{KySP7VJ}~}, ~{Q'IzJ}A?~});
    printf("~{H+0`F=>y7VJG#:~}%.2f\n", ~{F=>y7V~});

    /*
     * ~{RTOBJGR;P)VPND1j5c7{:E2bJT#:~}
     * ~{>d:E!#NJ:E#?8PL>:E#!6::E#,6Y:E!"C0:E#:7V:E#;~}
     * ~{R}:E~}""''~{@(:E#(#)!6!7!>!?#{#}~}
     */

    return 0;  // ~{U}3#MK3v~}
}