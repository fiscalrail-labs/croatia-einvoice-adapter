import readline from "node:readline";
import { validate } from "verifaktura";
import { buildUbl } from "@verifaktura/build";
import { HR_CUSTOMIZATION_ID } from "@verifaktura/cius-hr";
import "@verifaktura/cius-hr";

const VERSION = "0.3.0";

function party(party, operator = null) {
  const oib = String(party.oib).replace(/^HR/, "");
  return {
    name: party.name,
    vatId: `HR${oib}`,
    legalId: oib,
    legalIdScheme: "9934",
    electronicAddress: { value: oib, scheme: "9934" },
    address: {
      street: party.address.street,
      city: party.address.city,
      postalCode: party.address.postal_code,
      country: party.address.country_code ?? "HR"
    },
    ...(operator ? { contact: { name: operator, id: oib } } : {})
  };
}

function invoiceModel(input) {
  return {
    customizationId: HR_CUSTOMIZATION_ID,
    profileId: input.profile_id,
    id: input.invoice_number,
    issueDate: input.issue_date,
    issueTime: input.issue_time,
    dueDate: input.due_date,
    deliveryDate: input.delivery_date ?? input.issue_date,
    typeCode: "380",
    currency: input.currency,
    seller: party(input.supplier, input.supplier_operator_name),
    buyer: party(input.customer),
    paymentReference: input.payment_id,
    paymentMeans: {
      code: "30",
      description: "Credit transfer",
      accountId: input.supplier_iban
    },
    lines: input.lines.map((line, index) => ({
      id: String(index + 1),
      name: line.description,
      quantity: String(line.quantity),
      unitPrice: String(line.unit_price),
      unitCode: line.unit_code,
      vatCategory: "S",
      vatRate: String(line.vat_rate),
      vatCategoryName: `HR:PDV${line.vat_rate}`,
      classification: { value: line.kpd_code, scheme: "CG" }
    }))
  };
}

async function processRequest(request) {
  const op = request.op;
  if (op === "ping") {
    return {
      ready: true,
      workerVersion: VERSION,
      engine: "verifaktura/0.1.8",
      hrProfile: "2026-03-15"
    };
  }

  if (op === "generate") {
    const xml = buildUbl(invoiceModel(request.invoice));
    return { xml };
  }

  if (op === "validate") {
    return await validate(request.xml, {
      lang: request.lang ?? "en",
      profiles: ["hr"],
      maxIssues: request.maxIssues ?? 200
    });
  }

  if (op === "preflight") {
    const xml = buildUbl(invoiceModel(request.invoice));
    const report = await validate(xml, {
      lang: request.lang ?? "en",
      profiles: ["hr"],
      maxIssues: request.maxIssues ?? 200
    });
    return { xml, report };
  }

  throw new Error(`Unknown operation: ${op}`);
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  let id = null;
  try {
    const request = JSON.parse(line);
    id = request.id ?? null;
    const result = await processRequest(request);
    process.stdout.write(`${JSON.stringify({ id, ok: true, result })}\n`);
  } catch (error) {
    process.stdout.write(`${JSON.stringify({
      id,
      ok: false,
      error: error instanceof Error ? error.message : String(error)
    })}\n`);
  }
}
