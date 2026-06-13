export type Priority = "High" | "Medium" | "Low"
export type Status = "Open" | "Assigned" | "In Progress" | "Resolved"

export type Ticket = {
  id: string
  client: string
  facility: string
  asset: string
  priority: Priority
  status: Status
  technician: string | null
  created: string
  fault?: string
}

export const tickets: Ticket[] = [
  {
    id: "TK-4821",
    client: "Northwind Logistics",
    facility: "Dallas Distribution Center",
    asset: "HVAC Unit RTU-04",
    priority: "High",
    status: "In Progress",
    technician: "Marcus Hill",
    created: "2026-06-12",
    fault: "Compressor overheating, intermittent shutdowns during peak load.",
  },
  {
    id: "TK-4820",
    client: "Aurora Health Systems",
    facility: "St. Mary Wing B",
    asset: "Backup Generator GEN-02",
    priority: "High",
    status: "Assigned",
    technician: "Priya Nair",
    created: "2026-06-12",
    fault: "Generator failing weekly self-test, fault code E-17.",
  },
  {
    id: "TK-4819",
    client: "Cedar Foods Mfg.",
    facility: "Plant 3 - Packaging",
    asset: "Conveyor Belt CB-11",
    priority: "Medium",
    status: "Open",
    technician: null,
    created: "2026-06-11",
    fault: "Belt tracking off-center, occasional product jams.",
  },
  {
    id: "TK-4818",
    client: "Northwind Logistics",
    facility: "Phoenix Cross-Dock",
    asset: "Dock Leveler DL-07",
    priority: "Low",
    status: "Resolved",
    technician: "Dana Foster",
    created: "2026-06-10",
    fault: "Hydraulic leveler slow to rise.",
  },
  {
    id: "TK-4817",
    client: "Summit Retail Group",
    facility: "Store #214 - Denver",
    asset: "Walk-in Cooler WC-02",
    priority: "High",
    status: "Open",
    technician: null,
    created: "2026-06-11",
    fault: "Cooler not holding temperature, reading 48°F.",
  },
  {
    id: "TK-4816",
    client: "Aurora Health Systems",
    facility: "Imaging Center",
    asset: "Chiller CH-01",
    priority: "Medium",
    status: "In Progress",
    technician: "Marcus Hill",
    created: "2026-06-10",
    fault: "Chiller making abnormal noise, vibration alarm.",
  },
  {
    id: "TK-4815",
    client: "Cedar Foods Mfg.",
    facility: "Plant 1 - Cold Storage",
    asset: "Refrigeration Compressor RC-09",
    priority: "Medium",
    status: "Assigned",
    technician: "Dana Foster",
    created: "2026-06-09",
    fault: "Pressure fluctuations on low side.",
  },
  {
    id: "TK-4814",
    client: "Summit Retail Group",
    facility: "Store #198 - Boulder",
    asset: "Rooftop AC RTU-12",
    priority: "Low",
    status: "Resolved",
    technician: "Priya Nair",
    created: "2026-06-08",
    fault: "Routine filter replacement and inspection.",
  },
  {
    id: "TK-4813",
    client: "Northwind Logistics",
    facility: "Dallas Distribution Center",
    asset: "Forklift Charger FC-03",
    priority: "Low",
    status: "Open",
    technician: null,
    created: "2026-06-09",
    fault: "Charger port #2 not initiating charge cycle.",
  },
]

export type Technician = {
  name: string
  role: string
  available: boolean
}

export const technicians: Technician[] = [
  { name: "Marcus Hill", role: "Senior HVAC Tech", available: false },
  { name: "Priya Nair", role: "Electrical Specialist", available: true },
  { name: "Dana Foster", role: "Mechanical Tech", available: true },
  { name: "Leo Tan", role: "Refrigeration Tech", available: true },
  { name: "Sara Bloom", role: "Field Engineer", available: false },
]

export type Part = {
  sku: string
  name: string
  stock: number
  threshold: number
}

export const parts: Part[] = [
  { sku: "FLT-2002", name: 'Pleated Air Filter 20x20', stock: 4, threshold: 10 },
  { sku: "CAP-4410", name: "Run Capacitor 45/5 µF", stock: 2, threshold: 8 },
  { sku: "BLT-1187", name: "Conveyor Drive Belt", stock: 12, threshold: 6 },
  { sku: "RLY-3300", name: "Contactor Relay 40A", stock: 3, threshold: 10 },
  { sku: "REF-R410", name: "Refrigerant R-410A (lb)", stock: 28, threshold: 15 },
  { sku: "SNS-9021", name: "Temperature Sensor Probe", stock: 1, threshold: 6 },
]

export const facilities = [
  "Dallas Distribution Center",
  "Phoenix Cross-Dock",
  "St. Mary Wing B",
  "Imaging Center",
  "Plant 3 - Packaging",
  "Plant 1 - Cold Storage",
  "Store #214 - Denver",
]

export const assetsByFacility: Record<string, string[]> = {
  "Dallas Distribution Center": ["HVAC Unit RTU-04", "Forklift Charger FC-03", "Loading Bay Lights"],
  "Phoenix Cross-Dock": ["Dock Leveler DL-07", "Rooftop AC RTU-08"],
  "St. Mary Wing B": ["Backup Generator GEN-02", "Boiler BLR-01"],
  "Imaging Center": ["Chiller CH-01", "Air Handler AHU-05"],
  "Plant 3 - Packaging": ["Conveyor Belt CB-11", "Shrink Wrapper SW-02"],
  "Plant 1 - Cold Storage": ["Refrigeration Compressor RC-09", "Walk-in Freezer WF-01"],
  "Store #214 - Denver": ["Walk-in Cooler WC-02", "Rooftop AC RTU-12"],
}

export type TechJob = {
  id: string
  client: string
  facility: string
  asset: string
  priority: Priority
  address: string
  window: string
  fault: string
}

export const technicianJobs: TechJob[] = [
  {
    id: "TK-4821",
    client: "Northwind Logistics",
    facility: "Dallas Distribution Center",
    asset: "HVAC Unit RTU-04",
    priority: "High",
    address: "4400 Logistics Pkwy, Dallas, TX",
    window: "Today · 9:00–11:00 AM",
    fault: "Compressor overheating, intermittent shutdowns during peak load.",
  },
  {
    id: "TK-4816",
    client: "Aurora Health Systems",
    facility: "Imaging Center",
    asset: "Chiller CH-01",
    priority: "Medium",
    address: "210 Medical Dr, Plano, TX",
    window: "Today · 1:00–3:00 PM",
    fault: "Chiller making abnormal noise, vibration alarm.",
  },
  {
    id: "TK-4809",
    client: "Summit Retail Group",
    facility: "Store #214 - Denver",
    asset: "Walk-in Cooler WC-02",
    priority: "High",
    address: "88 Market St, Denver, CO",
    window: "Tomorrow · 8:30–10:00 AM",
    fault: "Cooler not holding temperature, follow-up inspection.",
  },
]
