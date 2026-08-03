/**
 * Vector PDF for the embedded host, on the same export core the viewer uses.
 *
 * The shared normalisation and PDF writer live in
 * `editors/jsfcstm/src/diagram/export`, and this entry does not reimplement any
 * of it. What it adds is the DOM contract that code assumes: a browser supplies
 * `DOMParser`, `XMLSerializer` and CSS selector queries, and the embedded host
 * supplies none of them.
 *
 * The selector support is deliberately closed. `xmldom` has no selector engine,
 * and a shim that answered every query with an empty list would make the halo
 * removal in `prepareSvgForPdf` silently do nothing -- the PDF would still be
 * produced, with a stroke halo baked into every transition label. Only the two
 * selectors the export core actually uses are answered; anything else throws, so
 * a future selector arrives as a loud failure rather than a quiet omission.
 */
import { DOMImplementation, DOMParser, XMLSerializer } from "@xmldom/xmldom";

import { renderVectorPdf } from "../../editors/jsfcstm/src/diagram/export";

interface PdfRequest {
    svg: string;
    width: number;
    height: number;
}

interface PdfJob {
    status: "pending" | "done" | "error";
    pdf?: string;
    error?: string;
}

interface PdfGlobal {
    DOMParser?: unknown;
    XMLSerializer?: unknown;
    document?: unknown;
    __pyfcstm_resvg_expand?: (svg: string) => string;
    __pyfcstm_pdf_start?: (requestJson: string, requestId: string) => string;
    __pyfcstm_pdf_poll?: (requestId: string) => string;
    __pyfcstm_pdf_drop?: (requestId: string) => boolean;
}

const pdfGlobal = globalThis as unknown as PdfGlobal;

const BASE64_ALPHABET =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

/**
 * Encode bytes as base64, since the host has `atob` but no `btoa`.
 */
function encodeBase64(bytes: Uint8Array): string {
    let output = "";
    for (let index = 0; index < bytes.length; index += 3) {
        const first = bytes[index];
        const second = bytes[index + 1];
        const third = bytes[index + 2];
        output += BASE64_ALPHABET[first >> 2];
        output += BASE64_ALPHABET[((first & 3) << 4) | (second === undefined ? 0 : second >> 4)];
        output +=
            second === undefined
                ? "="
                : BASE64_ALPHABET[((second & 15) << 2) | (third === undefined ? 0 : third >> 6)];
        output += third === undefined ? "=" : BASE64_ALPHABET[third & 63];
    }
    return output;
}

/** Collect descendants of `node` for which `accept` holds, in document order. */
function collectDescendants(
    node: any,
    accept: (candidate: any) => boolean,
    found: any[],
): void {
    const children = node.childNodes;
    if (!children) return;
    for (let index = 0; index < children.length; index += 1) {
        const child = children[index];
        // 1 is ELEMENT_NODE; text and comment nodes have no attributes to match.
        if (child.nodeType !== 1) continue;
        if (accept(child)) found.push(child);
        collectDescendants(child, accept, found);
    }
}

/** Report whether `element` sits inside a transition label group. */
function insideTransitionLabel(element: any): boolean {
    let parent = element.parentNode;
    while (parent && parent.nodeType === 1) {
        if (
            typeof parent.getAttribute === "function" &&
            parent.getAttribute("data-fcstm-kind") === "transition-label"
        ) {
            return true;
        }
        parent = parent.parentNode;
    }
    return false;
}

/**
 * Install the DOM contract the shared export core expects.
 *
 * @param elementPrototype Prototype every parsed element inherits from.
 */
function installDomContract(elementPrototype: any): void {
    if (!elementPrototype.querySelectorAll) {
        elementPrototype.querySelectorAll = function (selector: string): any[] {
            const wanted = String(selector).trim();
            if (wanted === "style,link" || wanted === "style, link") {
                const found: any[] = [];
                collectDescendants(
                    this,
                    candidate => {
                        const name = String(candidate.nodeName).toLowerCase();
                        return name === "style" || name === "link";
                    },
                    found,
                );
                return found;
            }
            if (
                wanted ===
                '[data-fcstm-kind="transition-label"] text[paint-order="stroke"]'
            ) {
                const found: any[] = [];
                collectDescendants(
                    this,
                    candidate =>
                        String(candidate.nodeName).toLowerCase() === "text" &&
                        typeof candidate.getAttribute === "function" &&
                        candidate.getAttribute("paint-order") === "stroke" &&
                        insideTransitionLabel(candidate),
                    found,
                );
                return found;
            }
            throw new Error(
                "the embedded PDF host answers only the export core's own " +
                    "selectors; got " + wanted,
            );
        };
    }
    if (!("id" in elementPrototype)) {
        // `svg2pdf.js` tests `hasAttribute("id")` and then reads `.id`, which
        // `xmldom` does not expose as a property. Without this the value reaching
        // the CSS identifier escaper is `undefined`.
        Object.defineProperty(elementPrototype, "id", {
            get(this: any) {
                const value = this.getAttribute("id");
                return value === null ? "" : value;
            },
            configurable: true,
        });
    }
}

if (!pdfGlobal.DOMParser) {
    pdfGlobal.DOMParser = DOMParser;
    pdfGlobal.XMLSerializer = XMLSerializer;
    const implementation = new DOMImplementation() as any;
    if (typeof implementation.createHTMLDocument !== "function") {
        // `svg2pdf.js` asks for a scratch HTML document while resolving styles.
        // `xmldom` implements the XML half of `DOMImplementation` only, so the
        // scratch document is an XML one carrying the `body` the caller expects.
        implementation.createHTMLDocument = function () {
            const scratch = new DOMImplementation().createDocument(
                "http://www.w3.org/1999/xhtml",
                "html",
                null,
            );
            const body = scratch.createElement("body");
            scratch.documentElement.appendChild(body);
            Object.defineProperty(scratch, "body", {
                value: body,
                configurable: true,
            });
            return scratch;
        };
    }
    const host = implementation.createDocument(null, null, null) as any;
    host.implementation = implementation;
    pdfGlobal.document = host;
    installDomContract(
        Object.getPrototypeOf(
            new DOMParser().parseFromString("<svg/>", "image/svg+xml")
                .documentElement,
        ),
    );
}
const jobs = new Map<string, PdfJob>();

function errorText(error: unknown): string {
    if (error instanceof Error) return error.message || String(error);
    return String(error);
}

/**
 * Render one request through the shared export core.
 */
function render(requestJson: string): Promise<string> {
    const request = JSON.parse(requestJson) as PdfRequest;
    const expander = pdfGlobal.__pyfcstm_resvg_expand;
    return renderVectorPdf(
        request.svg,
        { width: request.width, height: request.height },
        expander ? svg => Promise.resolve(expander(svg)) : undefined,
    ).then(bytes => encodeBase64(bytes));
}

pdfGlobal.__pyfcstm_pdf_start = (requestJson, requestId) => {
    const job: PdfJob = { status: "pending" };
    jobs.set(requestId, job);
    render(requestJson).then(
        pdf => {
            job.status = "done";
            job.pdf = pdf;
        },
        error => {
            job.status = "error";
            job.error = errorText(error);
        },
    );
    return requestId;
};

pdfGlobal.__pyfcstm_pdf_poll = requestId =>
    JSON.stringify(jobs.get(requestId) ?? { status: "error", error: "unknown job" });

pdfGlobal.__pyfcstm_pdf_drop = requestId => jobs.delete(requestId);
