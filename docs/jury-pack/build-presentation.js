const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

const C = {
  navy: "1B3A5C",
  navyDark: "152E4A",
  gold: "D4A843",
  white: "FFFFFF",
  offWhite: "F5F6F8",
  lightGray: "E8ECF0",
  midGray: "8C9AAE",
  darkText: "1E2D3D",
  bodyText: "333333",
  blue: "2E75B6",
  teal: "0D9488",
  green: "4CAF50",
  orange: "E8913A",
  red: "C0392B",
};

const FONT_HEADER = "Liberation Sans";
const FONT_BODY = "Liberation Sans";
const ROOT = path.resolve(__dirname, "../..");
const OUT = path.join(__dirname, "Sentinel-Command-Presentation.pptx");

async function iconToBase64Png(IconComponent, color = "#000000", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}

function addHeaderBar(slide, pres, title) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 13.333, h: 0.78,
    fill: { color: C.navy },
  });
  slide.addText(title, {
    x: 0.45, y: 0, w: 12.4, h: 0.78,
    fontSize: 16, fontFace: FONT_HEADER, color: C.white,
    bold: true, valign: "middle", margin: 0, charSpacing: 1.2,
  });
}

function addGoldStripe(slide, pres) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.08, h: 7.5,
    fill: { color: C.gold },
  });
}

function addFooter(slide, pres, page) {
  slide.addText("Sentinel Command  |  Gujarat Police Innovation Challenge 2026  |  Category 1 solo", {
    x: 0.45, y: 7.15, w: 11.2, h: 0.22,
    fontSize: 9, fontFace: FONT_BODY, color: C.midGray, margin: 0,
  });
  slide.addText(String(page), {
    x: 12.1, y: 7.15, w: 0.9, h: 0.22,
    fontSize: 9, fontFace: FONT_BODY, color: C.midGray, align: "right", margin: 0,
  });
}

const makeShadow = () => ({ type: "outer", color: "000000", blur: 4, offset: 2, angle: 135, opacity: 0.1 });

async function buildPresentation() {
  const {
    FaMapMarkedAlt, FaVideo, FaSearch, FaBell, FaShieldAlt,
    FaCheckCircle, FaCar, FaDatabase, FaNetworkWired, FaExpand,
  } = require("react-icons/fa");

  const iconMap = await iconToBase64Png(FaMapMarkedAlt, "#FFFFFF", 256);
  const iconVideo = await iconToBase64Png(FaVideo, "#FFFFFF", 256);
  const iconSearch = await iconToBase64Png(FaSearch, "#FFFFFF", 256);
  const iconBell = await iconToBase64Png(FaBell, "#FFFFFF", 256);
  const iconShield = await iconToBase64Png(FaShieldAlt, "#FFFFFF", 256);
  const iconCheck = await iconToBase64Png(FaCheckCircle, "#4CAF50", 256);
  const iconCar = await iconToBase64Png(FaCar, "#FFFFFF", 256);
  const iconDb = await iconToBase64Png(FaDatabase, "#FFFFFF", 256);
  const iconNet = await iconToBase64Png(FaNetworkWired, "#FFFFFF", 256);
  const iconExpand = await iconToBase64Png(FaExpand, "#FFFFFF", 256);

  const archPath = path.join(ROOT, "docs/diagrams/sentinel-architecture.png");
  const huntPath = path.join(ROOT, "docs/diagrams/hunt-watchlist-flow.png");

  const pres = new pptxgen();
  pres.defineLayout({ name: "WIDE16x9", width: 13.333, height: 7.5 });
  pres.layout = "WIDE16x9";
  pres.author = "Nikhil";
  pres.title = "Sentinel Command — Gujarat Police Innovation Challenge 2026";
  pres.subject = "Hybrid Model 1 + 2 CCTV registry, ANPR, watchlist, hunt";

  // ── SLIDE 1 TITLE ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.navy };
    addGoldStripe(slide, pres);
    slide.addText("GUJARAT POLICE INNOVATION CHALLENGE 2026", {
      x: 0.7, y: 1.15, w: 11.5, h: 0.35,
      fontSize: 13, fontFace: FONT_BODY, color: C.gold, bold: true, charSpacing: 2, margin: 0,
    });
    slide.addText("SENTINEL COMMAND", {
      x: 0.7, y: 1.6, w: 11.5, h: 0.85,
      fontSize: 40, fontFace: FONT_HEADER, color: C.white, bold: true, margin: 0, charSpacing: 1,
    });
    slide.addText("A GIS camera registry and unified ANPR command layer\non the official Sentinel sandbox — Hybrid Model 1 + 2", {
      x: 0.7, y: 2.55, w: 10.5, h: 0.7,
      fontSize: 18, fontFace: FONT_BODY, color: C.lightGray, margin: 0,
    });
    const pills = [
      ["Category 1", "Student / solo"],
      ["Model", "Hybrid 1 + 2"],
      ["Sandbox", "30 official cameras"],
      ["Submit by", "15 Sep 2026"],
    ];
    pills.forEach((p, i) => {
      const x = 0.7 + i * 3.05;
      slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x, y: 3.55, w: 2.85, h: 1.15, fill: { color: C.navyDark }, rectRadius: 0.08,
      });
      slide.addText(p[0], {
        x, y: 3.62, w: 2.85, h: 0.4,
        fontSize: 11, fontFace: FONT_BODY, color: C.gold, align: "center", margin: 0,
      });
      slide.addText(p[1], {
        x, y: 4.0, w: 2.85, h: 0.5,
        fontSize: 14, fontFace: FONT_HEADER, color: C.white, bold: true, align: "center", margin: 0,
      });
    });
    slide.addText("Nikhil  ·  Working prototype, not a mock-up  ·  Consume official RTSP / HLS — do not replace departmental VMS", {
      x: 0.7, y: 6.85, w: 12, h: 0.3,
      fontSize: 12, fontFace: FONT_BODY, color: C.midGray, margin: 0,
    });
    slide.addNotes("Open with the one-line pitch: we do not rip out cameras. We map them, watch them, read plates, and hunt a number.");
  }

  // ── SLIDE 2 PROBLEM ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "THE PROBLEM  ·  WHY A COMMAND LAYER");
    addGoldStripe(slide, pres);
    const cards = [
      ["26 departments", "Independent CCTV estates. Analog and IP. Cloud and local NVR. 7-day vs 15-day retention."],
      ["No shared map", "Police cannot see where cameras sit, who owns them, or which feeds are live."],
      ["Many viewers", "Command centres jump between vendor players. No single hunt for a vehicle number."],
      ["Databases exist", "VAHAN, SARTHI, eGujCop, AFIS already hold stolen/wanted records — CCTV is not wired to them yet."],
    ];
    cards.forEach((c, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = 0.5 + col * 6.35;
      const y = 1.05 + row * 2.55;
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 6.05, h: 2.35, fill: { color: C.white }, shadow: makeShadow(),
      });
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 0.1, h: 2.35, fill: { color: C.gold },
      });
      slide.addText(c[0], {
        x: x + 0.35, y: y + 0.25, w: 5.45, h: 0.5,
        fontSize: 20, fontFace: FONT_HEADER, color: C.navy, bold: true, margin: 0,
      });
      slide.addText(c[1], {
        x: x + 0.35, y: y + 0.9, w: 5.45, h: 1.15,
        fontSize: 15, fontFace: FONT_BODY, color: C.bodyText, margin: 0,
      });
    });
    addFooter(slide, pres, "02");
    slide.addNotes("Official problem: heterogeneous infrastructure, 1000 km spread, analytics, scale to 80k. We solve the officer job today: map + watch + plate + hunt.");
  }

  // ── SLIDE 3 MODEL ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "CHOSEN APPROACH  ·  HYBRID MODEL 1 + 2");
    addGoldStripe(slide, pres);
    slide.addText("Model 1 is mandatory as the GIS foundation. We combine it with Model 2 so the registry is not a dead inventory — officers can watch, detect, and hunt.", {
      x: 0.5, y: 0.9, w: 12.3, h: 0.55,
      fontSize: 15, fontFace: FONT_BODY, color: C.bodyText, margin: 0,
    });
    const cols = [
      ["Model 1 — Registry", "Leaflet GIS pins, bulk CSV + API import from official cameras.json, department labels, gap report, registry CSV export."],
      ["Model 2 — Viewing + ANPR", "HLS player in one UI, RTSP TCP capture for AI, YOLOv8n vehicles, RapidOCR plates, events index, watchlist alerts, hunt trail."],
      ["Not running (roadmap)", "Model 3 vendor adapters / Kafka. Model 4 central VMS, face, live VAHAN. Named as Phase 2 adapters — not faked in this prototype."],
    ];
    cols.forEach((c, i) => {
      const x = 0.5 + i * 4.2;
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y: 1.6, w: 3.95, h: 4.55, fill: { color: C.white }, shadow: makeShadow(),
      });
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y: 1.6, w: 3.95, h: 0.7, fill: { color: i === 2 ? C.navyDark : C.navy },
      });
      slide.addText(c[0], {
        x, y: 1.6, w: 3.95, h: 0.7,
        fontSize: 15, fontFace: FONT_HEADER, color: C.white, bold: true, align: "center", valign: "middle", margin: 0,
      });
      slide.addText(c[1], {
        x: x + 0.22, y: 2.5, w: 3.5, h: 3.35,
        fontSize: 15, fontFace: FONT_BODY, color: C.bodyText, margin: 0,
      });
    });
    addFooter(slide, pres, "03");
    slide.addNotes("Justification: solo Category 1. Official page allows hybrid. Existing VMS stay independent — we consume RTSP/HLS only.");
  }

  // ── SLIDE 4 WHAT POLICE GET ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "WHAT THE OFFICER GETS  ·  WORKING TODAY");
    addGoldStripe(slide, pres);
    const items = [
      [iconMap, "GIS registry", "30 official cameras + own-feed clips on one Leaflet map. Filter, CSV import, coverage gap."],
      [iconVideo, "Unified watch", "HLS in-app player via session cookie proxy. Same catalogue as cctv.corp8.cloud."],
      [iconCar, "ANPR metadata", "YOLOv8n finds vehicles. RapidOCR reads close plates. Events stored with time and snapshot."],
      [iconBell, "Watchlist alerts", "Representative stolen/wanted list. Match fires a red banner and a beep. Allowed by the brief."],
      [iconSearch, "Cross-camera hunt", "Type a registration. Trail on the map. Timestamped hits. Export CSV for the file."],
      [iconShield, "Integrator-safe", "RTSP over TCP, PTS timing, backoff, consume-only. We never publish into their gateway."],
    ];
    items.forEach((it, i) => {
      const col = i % 3;
      const row = Math.floor(i / 3);
      const x = 0.5 + col * 4.2;
      const y = 1.05 + row * 2.85;
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 3.95, h: 2.6, fill: { color: C.white }, shadow: makeShadow(),
      });
      slide.addShape(pres.shapes.OVAL, {
        x: x + 0.25, y: y + 0.28, w: 0.5, h: 0.5, fill: { color: C.navy },
      });
      slide.addImage({ data: it[0], x: x + 0.35, y: y + 0.38, w: 0.3, h: 0.3 });
      slide.addText(it[1], {
        x: x + 0.9, y: y + 0.3, w: 2.8, h: 0.45,
        fontSize: 16, fontFace: FONT_HEADER, color: C.navy, bold: true, valign: "middle", margin: 0,
      });
      slide.addText(it[2], {
        x: x + 0.25, y: y + 1.0, w: 3.45, h: 1.35,
        fontSize: 14, fontFace: FONT_BODY, color: C.bodyText, margin: 0,
      });
    });
    addFooter(slide, pres, "04");
  }

  // ── SLIDE 5 ARCHITECTURE ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "ARCHITECTURE  ·  THEIR GRID + OUR COMMAND LAYER");
    addGoldStripe(slide, pres);
    const imgW = 8.4;
    const imgH = imgW * (680 / 1100);
    slide.addImage({
      path: archPath,
      x: 0.4, y: 0.95, w: imgW, h: imgH,
      sizing: { type: "contain", w: imgW, h: imgH },
    });
    slide.addText("Labels in the PNG: catalogue is now cameras.json; RTSP 103.250.160.189:8554 is open from this network; watch is HLS proxy, not iframe.", {
      x: 0.45, y: 6.55, w: 8.3, h: 0.45,
      fontSize: 11, fontFace: FONT_BODY, color: C.midGray, margin: 0,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 9.05, y: 0.95, w: 3.85, h: 5.55, fill: { color: C.navy },
    });
    slide.addText("Split of duties", {
      x: 9.25, y: 1.1, w: 3.45, h: 0.4,
      fontSize: 16, fontFace: FONT_HEADER, color: C.gold, bold: true, margin: 0,
    });
    slide.addText([
      { text: "Their side", options: { bold: true, breakLine: true } },
      { text: "Cameras, MediaMTX-style hub, password portal, RTSP + HLS.", options: { breakLine: true } },
      { text: "", options: { breakLine: true } },
      { text: "Our side", options: { bold: true, breakLine: true } },
      { text: "React UI, FastAPI, JSON registry, YOLO, OCR, hunt CSV.", options: { breakLine: true } },
      { text: "", options: { breakLine: true } },
      { text: "Rule", options: { bold: true, breakLine: true } },
      { text: "We do not store 24-hour video. Short JPEG evidence only. Departmental NVRs stay.", options: {} },
    ], {
      x: 9.25, y: 1.6, w: 3.45, h: 4.5,
      fontSize: 13, fontFace: FONT_BODY, color: C.white, margin: 0,
    });
    addFooter(slide, pres, "05");
    slide.addNotes("Point at three lanes: official grid, our app, AI pipeline. HLS for watch, RTSP for AI.");
  }

  // ── SLIDE 6 FETCH CAMERAS ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "LIVE INTEGRATION  ·  OFFICIAL INTEGRATOR CONTRACT");
    addGoldStripe(slide, pres);
    const steps = [
      ["1", "Sign in", "POST /auth/login on cctv.corp8.cloud. Session cookie stays in the backend CookieJar."],
      ["2", "Catalogue", "GET /cameras.json — 30 rows (cam01…cam30). Never hard-code ids."],
      ["3", "Build URLs", "HLS https://cctv.corp8.cloud/cam04/index.m3u8\nRTSP rtsp://103.250.160.189:8554/stream/cam04"],
      ["4", "Watch vs AI", "Officer: HLS + hls.js via our proxy.\nANPR: OpenCV RTSP TCP, PTS timestamps, backoff 2s–30s."],
    ];
    steps.forEach((s, i) => {
      const y = 1.0 + i * 1.35;
      slide.addShape(pres.shapes.OVAL, {
        x: 0.55, y: y + 0.15, w: 0.55, h: 0.55, fill: { color: C.navy },
      });
      slide.addText(s[0], {
        x: 0.55, y: y + 0.15, w: 0.55, h: 0.55,
        fontSize: 16, fontFace: FONT_HEADER, color: C.white, bold: true, align: "center", valign: "middle", margin: 0,
      });
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 1.3, y, w: 11.5, h: 1.2, fill: { color: C.white }, shadow: makeShadow(),
      });
      slide.addText(s[1], {
        x: 1.55, y: y + 0.12, w: 11, h: 0.35,
        fontSize: 16, fontFace: FONT_HEADER, color: C.navy, bold: true, margin: 0,
      });
      slide.addText(s[2], {
        x: 1.55, y: y + 0.48, w: 11, h: 0.6,
        fontSize: 14, fontFace: FONT_BODY, color: C.bodyText, margin: 0,
      });
    });
    addFooter(slide, pres, "06");
  }

  // ── SLIDE 7 ANPR ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "AI ANALYTICS  ·  DETECT → CROP → READ → STORE");
    addGoldStripe(slide, pres);
    const pipe = [
      ["Capture", "FFmpeg / OpenCV samples ~1 JPEG/s. IST stamp. PTS-based time, not wall-clock per packet."],
      ["YOLO v8n", "Nano weights on CPU. Classes: car, motorcycle, bus, truck. Box + confidence."],
      ["RapidOCR", "Crop lower ~45% of the vehicle box. ONNX OCR. Normalize GJ-01-AB-1234 → GJ01AB1234."],
      ["Evidence", "Annotated JPEG + events.json. Raw frames can be deleted. Not a 24-hour DVR."],
    ];
    pipe.forEach((p, i) => {
      const x = 0.45 + i * 3.2;
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y: 1.05, w: 3.05, h: 3.55, fill: { color: C.white }, shadow: makeShadow(),
      });
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y: 1.05, w: 3.05, h: 0.7, fill: { color: C.navy },
      });
      slide.addText((i + 1) + "  " + p[0], {
        x, y: 1.05, w: 3.05, h: 0.7,
        fontSize: 16, fontFace: FONT_HEADER, color: C.white, bold: true, align: "center", valign: "middle", margin: 0,
      });
      slide.addText(p[1], {
        x: x + 0.18, y: 1.95, w: 2.7, h: 2.4,
        fontSize: 14, fontFace: FONT_BODY, color: C.bodyText, margin: 0,
      });
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.45, y: 4.8, w: 12.4, h: 1.7, fill: { color: C.navy },
    });
    slide.addText("Honest analytics note for judges", {
      x: 0.7, y: 4.95, w: 12, h: 0.35,
      fontSize: 14, fontFace: FONT_HEADER, color: C.gold, bold: true, margin: 0,
    });
    slide.addText("Own-feed boom-barrier clips yield readable plates (GJ01AB1234). Wide Paldi live junction (cam04) yielded 61 vehicles and 0 OCR plates — letters are too few pixels. We show both: vehicles on government feed, plates on close-up feed. Same pipeline.", {
      x: 0.7, y: 5.35, w: 12, h: 0.95,
      fontSize: 14, fontFace: FONT_BODY, color: C.white, margin: 0,
    });
    addFooter(slide, pres, "07");
  }

  // ── SLIDE 8 HUNT ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "JURY TEST  ·  WATCHLIST + HUNT A REGISTRATION");
    addGoldStripe(slide, pres);
    const imgW = 7.6;
    const imgH = imgW * (720 / 1100);
    slide.addImage({
      path: huntPath,
      x: 0.4, y: 0.95, w: imgW, h: imgH,
      sizing: { type: "contain", w: imgW, h: imgH },
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 8.25, y: 0.95, w: 4.65, h: 5.55, fill: { color: C.white }, shadow: makeShadow(),
    });
    slide.addText("When they give a number", {
      x: 8.45, y: 1.1, w: 4.25, h: 0.45,
      fontSize: 16, fontFace: FONT_HEADER, color: C.navy, bold: true, margin: 0,
    });
    slide.addText([
      { text: "1. Add it to Watchlist (optional).", options: { bullet: true, breakLine: true } },
      { text: "2. Hunt box → Find trail.", options: { bullet: true, breakLine: true } },
      { text: "3. Map polyline + hit list.", options: { bullet: true, breakLine: true } },
      { text: "4. Export CSV for the file.", options: { bullet: true, breakLine: true } },
      { text: "If empty: Capture 4 / 5 / 12, Detect, Hunt again. That is the product, not a failure.", options: { bullet: true } },
    ], {
      x: 8.45, y: 1.65, w: 4.25, h: 3.2,
      fontSize: 14, fontFace: FONT_BODY, color: C.bodyText, paraSpaceAfter: 8,
    });
    slide.addText("Demo seed: GJ01AB1234 — 13 hits, Gate + Paldi own-feed.", {
      x: 8.45, y: 5.05, w: 4.25, h: 1.15,
      fontSize: 13, fontFace: FONT_BODY, color: C.navy, bold: true, margin: 0,
    });
    addFooter(slide, pres, "08");
  }

  // ── SLIDE 9 TECH ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "STACK  ·  OPEN, VENDOR-NEUTRAL, MATCHES THEIR SUGGESTED TOOLS");
    addGoldStripe(slide, pres);
    const rows = [
      [
        { text: "Layer", options: { bold: true, color: C.white, fill: { color: C.navy } } },
        { text: "Choice", options: { bold: true, color: C.white, fill: { color: C.navy } } },
        { text: "Why", options: { bold: true, color: C.white, fill: { color: C.navy } } },
      ],
      ["UI", "React 19 + Vite 6", "Official suggested React.js"],
      ["Map", "Leaflet + OSM", "Official Model 1 GIS suggestion"],
      ["API", "Python FastAPI", "Official suggested Python / FastAPI"],
      ["Store now", "JSON files", "Solo speed. Postgres + PostGIS on the scale slide"],
      ["Watch", "HLS + hls.js proxy", "HTTPS 443, cookie, AES-128 playlists"],
      ["AI ingest", "OpenCV RTSP TCP", "Integrator guide: tcp, PTS, backoff"],
      ["Detect", "YOLOv8n (nano)", "CPU-capable vehicle boxes"],
      ["OCR", "RapidOCR ONNX", "Plate text from crop"],
    ];
    const tableRows = rows.map((r, idx) => {
      if (idx === 0) return r;
      const fill = idx % 2 === 0 ? C.offWhite : C.white;
      return r.map((cell, ci) => ({
        text: cell,
        options: {
          fontSize: 13, fontFace: FONT_BODY, color: C.darkText,
          fill: { color: fill }, valign: "middle", margin: [5, 8, 5, 8],
          bold: ci === 0,
        },
      }));
    });
    slide.addTable(tableRows, {
      x: 0.5, y: 1.0, w: 12.3, colW: [2.2, 3.6, 6.5],
      border: { pt: 0.5, color: C.lightGray },
      fontFace: FONT_BODY,
      color: C.darkText,
      fontSize: 13,
    });
    addFooter(slide, pres, "09");
  }

  // ── SLIDE 10 RESULTS ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "MEASURED ON THIS PROTOTYPE  ·  NOT A CONCEPT VIDEO");
    addGoldStripe(slide, pres);
    const stats = [
      ["33", "cameras in registry", "30 official + 3 own-feed"],
      ["30", "from cameras.json", "Ahmedabad to Gandhidham"],
      ["61", "live Paldi vehicles", "cam04 RTSP TCP sample"],
      ["13", "GJ01AB1234 hits", "Gate + Paldi own-feed hunt"],
    ];
    stats.forEach((s, i) => {
      const x = 0.5 + i * 3.2;
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y: 1.1, w: 3.0, h: 2.35, fill: { color: C.navy },
      });
      slide.addText(s[0], {
        x, y: 1.25, w: 3.0, h: 0.95,
        fontSize: 36, fontFace: FONT_HEADER, color: C.gold, bold: true, align: "center", margin: 0,
      });
      slide.addText(s[1], {
        x: x + 0.1, y: 2.2, w: 2.8, h: 0.5,
        fontSize: 14, fontFace: FONT_HEADER, color: C.white, bold: true, align: "center", margin: 0,
      });
      slide.addText(s[2], {
        x: x + 0.1, y: 2.7, w: 2.8, h: 0.5,
        fontSize: 12, fontFace: FONT_BODY, color: C.lightGray, align: "center", margin: 0,
      });
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 3.7, w: 12.3, h: 2.7, fill: { color: C.white }, shadow: makeShadow(),
    });
    slide.addText("Two-system proof (Model 2 deliverable)", {
      x: 0.75, y: 3.9, w: 11.8, h: 0.4,
      fontSize: 16, fontFace: FONT_HEADER, color: C.navy, bold: true, margin: 0,
    });
    slide.addText("System A — official Sentinel grid (HLS watch + RTSP AI). System B — local MP4s treated as cameras. Same Extract / Detect / Hunt code path. Existing departmental storage is untouched.", {
      x: 0.75, y: 4.4, w: 11.8, h: 0.7,
      fontSize: 15, fontFace: FONT_BODY, color: C.bodyText, margin: 0,
    });
    slide.addText("Sandbox publishes ~30 cameras, not 50. We onboard every id in cameras.json. Statewide 80k is a scale plan, not this laptop.", {
      x: 0.75, y: 5.2, w: 11.8, h: 0.85,
      fontSize: 15, fontFace: FONT_BODY, color: C.bodyText, margin: 0,
    });
    addFooter(slide, pres, "10");
  }

  // ── SLIDE 11 SCALE ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "SCALE TO ~80,000  ·  SAME APIS, MORE MACHINES");
    addGoldStripe(slide, pres);
    const phases = [
      ["Now", "JSON store, one node, 30–40 cameras, file + official catalogue, CPU YOLO."],
      ["Phase 2", "PostgreSQL + PostGIS, Redis watchlist, object storage for snapshots, simple RBAC."],
      ["Phase 3", "Zone RTSP workers, queue (Kafka/RabbitMQ), horizontal API, GPU batching, HLS edge cache."],
      ["Phase 4", "VAHAN / SARTHI / eGujCop adapters, optional face, HA + DR, regional PoPs."],
    ];
    phases.forEach((p, i) => {
      const y = 1.05 + i * 1.25;
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0.5, y, w: 2.3, h: 1.1, fill: { color: C.navy },
      });
      slide.addText(p[0], {
        x: 0.5, y, w: 2.3, h: 1.1,
        fontSize: 16, fontFace: FONT_HEADER, color: C.white, bold: true, align: "center", valign: "middle", margin: 0,
      });
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 2.9, y, w: 9.9, h: 1.1, fill: { color: C.white }, shadow: makeShadow(),
      });
      slide.addText(p[1], {
        x: 3.15, y, w: 9.45, h: 1.1,
        fontSize: 16, fontFace: FONT_BODY, color: C.bodyText, valign: "middle", margin: 0,
      });
    });
    addFooter(slide, pres, "11");
    slide.addNotes("Cost sketch if asked: analytics GPUs at zone, not 80k central transcodes. Keep video at source. Metadata is cheap.");
  }

  // ── SLIDE 12 SECURITY + LIMITS ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.offWhite };
    addHeaderBar(slide, pres, "SECURITY, INTEROP, AND HONEST LIMITS");
    addGoldStripe(slide, pres);
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 1.05, w: 6.05, h: 5.35, fill: { color: C.white }, shadow: makeShadow(),
    });
    slide.addText("Built in", {
      x: 0.75, y: 1.2, w: 5.55, h: 0.4,
      fontSize: 18, fontFace: FONT_HEADER, color: C.navy, bold: true, margin: 0,
    });
    slide.addText([
      { text: "Consume-only. Never publish to the gateway.", options: { bullet: true, breakLine: true } },
      { text: "Grid password in .env — not in git.", options: { bullet: true, breakLine: true } },
      { text: "RTSP TCP, PTS timing, join warnings not fatal.", options: { bullet: true, breakLine: true } },
      { text: "Open protocols: RTSP, HLS, REST JSON.", options: { bullet: true, breakLine: true } },
      { text: "No 24h central archive — evidence JPEGs only.", options: { bullet: true } },
    ], {
      x: 0.75, y: 1.75, w: 5.55, h: 4.2,
      fontSize: 15, fontFace: FONT_BODY, color: C.bodyText, paraSpaceAfter: 10,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 6.8, y: 1.05, w: 6.05, h: 5.35, fill: { color: C.navy },
    });
    slide.addText("Not this laptop", {
      x: 7.05, y: 1.2, w: 5.55, h: 0.4,
      fontSize: 18, fontFace: FONT_HEADER, color: C.gold, bold: true, margin: 0,
    });
    slide.addText("No live VAHAN. No face. No Kafka. No department SSO. ANPR on distant junctions is vehicle-first. Continuous 30-camera workers are a scale step, not the demo. We say this so the jury can trust the rest.", {
      x: 7.05, y: 1.8, w: 5.55, h: 4.1,
      fontSize: 16, fontFace: FONT_BODY, color: C.white, margin: 0,
    });
    addFooter(slide, pres, "12");
  }

  // ── SLIDE 13 DEMO SCRIPT + CLOSE ──
  {
    const slide = pres.addSlide();
    slide.background = { color: C.navy };
    addGoldStripe(slide, pres);
    slide.addText("8-MINUTE LIVE DEMO", {
      x: 0.7, y: 0.4, w: 12, h: 0.45,
      fontSize: 14, fontFace: FONT_BODY, color: C.gold, bold: true, charSpacing: 2, margin: 0,
    });
    slide.addText("UI already running at localhost:5174", {
      x: 0.7, y: 0.85, w: 12, h: 0.4,
      fontSize: 22, fontFace: FONT_HEADER, color: C.white, bold: true, margin: 0,
    });
    const demo = [
      ["0:00", "Map + pitch", "Hybrid 1+2. Registry first. Existing VMS stay."],
      ["0:40", "Fetch grid", "cameras.json → 30 pins. Export registry CSV."],
      ["1:20", "Live watch", "Camera 4 / 12 HLS player."],
      ["2:10", "Own-feed ANPR", "Gate → Extract → Detect. Readable plate."],
      ["3:20", "Watchlist", "GJ01AB1234 → red STOLEN PLATE banner."],
      ["4:00", "Hunt + CSV", "Trail on map. This is the scoring test."],
      ["5:00", "Gov feed AI", "Paldi Capture → Detect vehicles + times."],
      ["6:20", "Scale slide", "Postgres, zone workers, VAHAN adapter later."],
      ["7:20", "Their number", "Paste designated registration into Hunt."],
    ];
    demo.forEach((d, i) => {
      const y = 1.4 + i * 0.55;
      slide.addText(d[0], {
        x: 0.7, y, w: 1.1, h: 0.5,
        fontSize: 13, fontFace: FONT_HEADER, color: C.gold, bold: true, valign: "middle", margin: 0,
      });
      slide.addText(d[1], {
        x: 1.9, y, w: 2.4, h: 0.5,
        fontSize: 14, fontFace: FONT_HEADER, color: C.white, bold: true, valign: "middle", margin: 0,
      });
      slide.addText(d[2], {
        x: 4.4, y, w: 8.3, h: 0.5,
        fontSize: 14, fontFace: FONT_BODY, color: C.lightGray, valign: "middle", margin: 0,
      });
    });
    slide.addNotes("If Hunt is empty for their plate: Capture 4, 5, 12 then Detect, then Hunt. Do not freeze.");
  }

  await pres.writeFile({ fileName: OUT });
  console.log("Wrote", OUT);
}

buildPresentation().catch((err) => {
  console.error(err);
  process.exit(1);
});
