import {
  AddEquation,
  BufferAttribute,
  BufferGeometry,
  CanvasTexture,
  CustomBlending,
  DoubleSide,
  Group,
  LineLoop,
  LineSegments,
  Matrix4,
  Mesh,
  OneFactor,
  PerspectiveCamera,
  Plane,
  PlaneGeometry,
  Points,
  Raycaster,
  RingGeometry,
  Scene,
  ShaderMaterial,
  SphereGeometry,
  SRGBColorSpace,
  SrcAlphaFactor,
  Sprite,
  SpriteMaterial,
  Vector2,
  Vector3,
  WebGLRenderer,
  ZeroFactor,
} from 'three'
import { ZODIAC_BY_ID, PROJECTED } from '../hero/zodiac.js'
import { ZODIAC_ART } from '../hero/zodiacArt.js'
import { SIGN_LIST } from '../cabinet/astro.js'
import { BELT, EARTH_RADIUS, MOON_ORBIT, ORBITS, toward } from './geometry.js'

/**
 * The game's sky in three.js (NatalGame drives it): the Sun with the planets on their orbits, the
 * belt of twelve signs around them with each constellation standing up behind its sector, the
 * rays of sight from the Earth, and the bursts when a ray finds its sign. Every colour is written
 * as it should look on screen, the glows add light over whatever lies beneath (the canvas is
 * transparent: the game's own backdrop, and at the very end the site's sky with the wheel).
 *
 * The scene knows nothing of the rules: it is told where everything stands and how bright it is,
 * and draws one frame when asked.
 */

const RAD = Math.PI / 180
const TAU = Math.PI * 2

/** Glows only add light: the canvas keeps its transparency where nothing solid is drawn. */
const GLOW = {
  transparent: true,
  depthWrite: false,
  blending: CustomBlending,
  blendEquation: AddEquation,
  blendSrc: SrcAlphaFactor,
  blendDst: OneFactor,
  blendSrcAlpha: ZeroFactor,
  blendDstAlpha: OneFactor,
}

const vec3 = (hex) => new Vector3(((hex >> 16) & 255) / 255, ((hex >> 8) & 255) / 255, (hex & 255) / 255)
const tints = new Map()
/** The same colour as `vec3`, kept: for colours set every frame. */
const tint = (hex) => {
  if (!tints.has(hex)) tints.set(hex, vec3(hex))
  return tints.get(hex)
}
/** A flat point [x, y] in the scene: the ecliptic is the XZ plane, north up. */
const place = (target, xy, h = 0) => target.set(xy[0], h, -xy[1])

export const GOLD = 0xf0cd8a
export const PALE = 0xfff1d6

/* ---- Shaders ---- */

const NOISE = /* glsl */ `
float hash3(vec3 p) {
  p = fract(p * 0.3183099 + 0.1);
  p *= 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}
float noise3(vec3 x) {
  vec3 i = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(mix(hash3(i), hash3(i + vec3(1, 0, 0)), f.x), mix(hash3(i + vec3(0, 1, 0)), hash3(i + vec3(1, 1, 0)), f.x), f.y),
    mix(mix(hash3(i + vec3(0, 0, 1)), hash3(i + vec3(1, 0, 1)), f.x), mix(hash3(i + vec3(0, 1, 1)), hash3(i + vec3(1, 1, 1)), f.x), f.y),
    f.z);
}
float fbm(vec3 p) {
  float a = 0.5;
  float s = 0.0;
  for (int i = 0; i < 4; i++) {
    s += a * noise3(p);
    p = p * 2.03 + vec3(1.7, 9.2, 3.1);
    a *= 0.5;
  }
  return s;
}
`

const BILLBOARD_VERT = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`

/** A soft round glow, or a thin ring of light (`uRing` > 0: its radius in the quad). */
const GLOW_FRAG = /* glsl */ `
uniform vec3 uColor;
uniform float uAlpha;
uniform float uSharp;
uniform float uRing;
varying vec2 vUv;
void main() {
  float d = length(vUv - 0.5) * 2.0;
  float a = uRing > 0.0
    ? exp(-pow((d - uRing) * 9.0, 2.0)) + 0.25 * exp(-d * d * 6.0) * step(d, 1.0)
    : pow(max(1.0 - d, 0.0), uSharp);
  gl_FragColor = vec4(uColor, a * uAlpha);
}
`

const SUN_VERT = /* glsl */ `
varying vec3 vN;
varying vec3 vP;
varying vec3 vView;
void main() {
  vP = position;
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vN = normalize(normalMatrix * normal);
  vView = normalize(-mv.xyz);
  gl_Position = projectionMatrix * mv;
}
`
const SUN_FRAG = /* glsl */ `
uniform float uTime;
varying vec3 vN;
varying vec3 vP;
varying vec3 vView;
${NOISE}
void main() {
  float mu = max(dot(normalize(vN), normalize(vView)), 0.0);
  float n = fbm(vP * 2.6 + vec3(0.0, uTime * 0.05, uTime * 0.08)) * 0.7 + noise3(vP * 9.0 - uTime * 0.2) * 0.3;
  vec3 core = vec3(1.0, 0.95, 0.8);
  vec3 edge = vec3(1.0, 0.52, 0.16);
  vec3 col = mix(edge, core, pow(mu, 0.55)) * (0.82 + 0.36 * n);
  gl_FragColor = vec4(col, 1.0);
}
`

/** The Sun's corona: a glow with slow rays turning in it. */
const CORONA_FRAG = /* glsl */ `
uniform float uTime;
uniform float uAlpha;
varying vec2 vUv;
void main() {
  vec2 c = vUv - 0.5;
  float d = length(c) * 2.0;
  float a = atan(c.y, c.x);
  float rays = 0.55 + 0.45 * sin(a * 7.0 + uTime * 0.15) * sin(a * 11.0 - uTime * 0.22);
  float glow = exp(-d * 5.2) * 1.4 + exp(-d * 2.2) * 0.35 * rays;
  glow *= smoothstep(1.0, 0.7, d);
  gl_FragColor = vec4(vec3(1.0, 0.78, 0.45) * glow, uAlpha);
}
`

const PLANET_VERT = /* glsl */ `
varying vec3 vN;
varying vec3 vW;
varying vec3 vLocal;
void main() {
  vLocal = position;
  vec4 w = modelMatrix * vec4(position, 1.0);
  vW = w.xyz;
  vN = normalize(mat3(modelMatrix) * normal);
  gl_Position = projectionMatrix * viewMatrix * w;
}
`
/** `uKind`: 0 — a rocky body, 1 — bands of cloud, 2 — the Earth, with seas, clouds and city lights at night. */
const PLANET_FRAG = /* glsl */ `
uniform vec3 uA;
uniform vec3 uB;
uniform vec3 uC;
uniform vec3 uRim;
uniform vec3 uSun;
uniform float uKind;
uniform float uBands;
uniform float uSeed;
uniform float uSelf;
uniform float uTime;
varying vec3 vN;
varying vec3 vW;
varying vec3 vLocal;
${NOISE}
void main() {
  vec3 n = normalize(vN);
  vec3 L = normalize(uSun - vW);
  vec3 V = normalize(cameraPosition - vW);
  float diff = dot(n, L);
  float day = smoothstep(-0.12, 0.3, diff);
  vec3 p = normalize(vLocal);
  vec3 base;
  float land = 0.0;
  if (uKind < 0.5) {
    float f = fbm(p * 2.4 + uSeed);
    base = mix(uA, uB, smoothstep(0.25, 0.75, f));
    base = mix(base, uC, smoothstep(0.55, 0.8, fbm(p * 6.0 + uSeed * 2.0)) * 0.8);
  } else if (uKind < 1.5) {
    float lat = p.y + 0.06 * fbm(p * 3.0 + uSeed);
    float b = sin(lat * uBands + fbm(p * 2.0 + uSeed) * 2.4) * 0.5 + 0.5;
    base = mix(uA, uB, b);
    base = mix(base, uC, smoothstep(0.6, 0.9, fbm(p * 5.0 + uSeed)) * 0.6);
  } else {
    land = smoothstep(0.5, 0.54, fbm(p * 2.1 + uSeed));
    base = mix(uA, uB, land);
    base = mix(base, vec3(0.93, 0.95, 1.0), smoothstep(0.8, 0.9, abs(p.y)));
    float cloud = smoothstep(0.5, 0.78, fbm(p * 3.6 + vec3(uTime * 0.015, 0.0, 0.0)));
    base = mix(base, vec3(1.0), cloud * 0.55);
  }
  vec3 col = base * (0.05 + 1.05 * day * max(diff, 0.0) + 0.12 * day);
  if (uKind > 1.5) {
    float lights = smoothstep(0.62, 0.78, fbm(p * 14.0 + uSeed)) * land;
    col += vec3(1.0, 0.72, 0.38) * lights * (1.0 - day) * 0.75;
  }
  float rim = pow(1.0 - max(dot(n, V), 0.0), 2.6);
  col += uRim * rim * (0.18 + 0.7 * day + uSelf * 0.6);
  col += uRim * uSelf * 0.08;
  gl_FragColor = vec4(col, 1.0);
}
`

/** Saturn's rings: bands of ice, lit by the Sun, a gap of Cassini. */
const RINGS_FRAG = /* glsl */ `
uniform vec3 uColor;
uniform float uAlpha;
varying vec2 vUv;
varying float vR;
void main() {
  float r = vR;
  float bands = 0.6 + 0.4 * sin(r * 46.0) * sin(r * 13.0 + 1.3);
  float cassini = 1.0 - 0.85 * exp(-pow((r - 0.72) * 30.0, 2.0));
  float edge = smoothstep(0.0, 0.08, r) * smoothstep(1.0, 0.9, r);
  gl_FragColor = vec4(uColor * bands, 0.75 * bands * cassini * edge * uAlpha);
}
`
const RINGS_VERT = /* glsl */ `
uniform float uInner;
uniform float uOuter;
varying vec2 vUv;
varying float vR;
void main() {
  vUv = uv;
  vR = (length(position.xy) - uInner) / (uOuter - uInner);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`

const LINE_VERT = /* glsl */ `
void main() {
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`
const LINE_FRAG = /* glsl */ `
uniform vec3 uColor;
uniform float uAlpha;
void main() {
  gl_FragColor = vec4(uColor, uAlpha);
}
`

/** The belt of signs: double rules, the dividers, the degree ticks, the lit sectors and the spot where a ray lands. */
const BELT_VERT = /* glsl */ `
varying vec2 vXY;
void main() {
  vXY = position.xy;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`
const BELT_FRAG = /* glsl */ `
uniform float uLit[12];
uniform float uTarget;
uniform float uPulse;
uniform vec2 uHit;
uniform float uTime;
uniform float uFade;
uniform vec3 uGold;
uniform float uInner;
uniform float uOuter;
varying vec2 vXY;
float rule(float d, float w, float aa) {
  return 1.0 - smoothstep(w, w + aa, abs(d));
}
void main() {
  float r = length(vXY);
  float deg = degrees(atan(vXY.y, vXY.x));
  if (deg < 0.0) deg += 360.0;
  int s = int(floor(deg / 30.0));
  float lit = 0.0;
  for (int i = 0; i < 12; i++) {
    if (i == s) lit = uLit[i];
  }
  float aa = fwidth(r) * 1.2;
  float span = uOuter - uInner;
  float rules = rule(r - uInner, 0.04, aa) + rule(r - uOuter, 0.04, aa)
    + 0.45 * rule(r - uInner - span * 0.09, 0.02, aa) + 0.45 * rule(r - uOuter + span * 0.09, 0.02, aa);
  float arc = 0.0174533 * r;
  float m30 = mod(deg, 30.0);
  float d30 = min(m30, 30.0 - m30) * arc;
  float daa = fwidth(d30) * 1.2;
  float dividers = rule(d30, 0.035, daa);
  float m5 = mod(deg, 5.0);
  float ticks = rule(min(m5, 5.0 - m5) * arc, 0.022, daa) * (1.0 - smoothstep(uInner + span * 0.16, uInner + span * 0.17, r));
  float m1 = mod(deg, 1.0);
  ticks += 0.55 * rule(min(m1, 1.0 - m1) * arc, 0.014, daa) * (1.0 - smoothstep(uInner + span * 0.08, uInner + span * 0.09, r));
  float lines = rules + dividers + ticks * 0.8;
  float across = (r - uInner) / span;
  float fill = 0.03 + lit * (0.16 + 0.16 * across);
  float target = float(s == int(uTarget)) * uPulse * (0.55 + 0.45 * sin(uTime * 3.2));
  vec2 spot = vec2(cos(radians(uHit.x)), sin(radians(uHit.x))) * (uInner + uOuter) * 0.5;
  float hd = length(vXY - spot);
  float hit = uHit.y * (exp(-hd * hd * 0.45) * 1.1 + exp(-hd * 0.6) * 0.25);
  vec3 col = uGold * (lines * (0.5 + lit * 0.7) + fill + target * 0.22) + vec3(1.0, 0.92, 0.75) * hit;
  gl_FragColor = vec4(col, uFade);
}
`

/** A constellation's stars: round, sized by magnitude, lit one by one as `uPop` runs from 0 to 1. */
const STAR_VERT = /* glsl */ `
attribute float size;
attribute float order;
uniform float uDpr;
uniform float uLight;
uniform float uPop;
uniform float uTime;
varying float vA;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  float pop = clamp((uPop - order * 0.7) / 0.3, 0.0, 1.0);
  float flare = pop * (1.0 - pop) * 4.0;
  float twinkle = 0.85 + 0.15 * sin(uTime * 2.0 + order * 31.0);
  vA = (0.35 + uLight * 0.65) * twinkle + flare * 0.6;
  gl_PointSize = size * uDpr * (0.8 + uLight * 0.45 + flare * 0.9);
}
`
const STAR_FRAG = /* glsl */ `
uniform float uAlpha;
uniform vec3 uColor;
varying float vA;
void main() {
  float d = length(gl_PointCoord - 0.5) * 2.0;
  float a = exp(-d * d * 5.0) + 0.5 * exp(-d * d * 40.0);
  gl_FragColor = vec4(uColor, a * vA * uAlpha * step(d, 1.0));
}
`

/** The background: thousands of faint stars twinkling at their own pace. */
const SKY_VERT = /* glsl */ `
attribute float size;
attribute float phase;
attribute vec3 tint;
uniform float uTime;
uniform float uDpr;
varying vec3 vTint;
varying float vA;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  vA = 0.72 + 0.28 * sin(uTime * (0.4 + phase * 1.4) + phase * 40.0);
  vTint = tint;
  gl_PointSize = size * uDpr;
}
`
const SKY_FRAG = /* glsl */ `
uniform float uAlpha;
varying vec3 vTint;
varying float vA;
void main() {
  float d = length(gl_PointCoord - 0.5) * 2.0;
  float a = exp(-d * d * 6.0);
  gl_FragColor = vec4(vTint, a * vA * uAlpha * step(d, 1.0));
}
`

/** A ray of sight: a bright core in a soft sheath, light running along it, a head while it shoots out. */
const BEAM_FRAG = /* glsl */ `
uniform vec3 uColor;
uniform float uPower;
uniform float uLen;
uniform float uHead;
uniform float uTime;
varying vec2 vUv;
void main() {
  float along = vUv.x;
  if (along > uHead) discard;
  float across = abs(vUv.y - 0.5) * 2.0;
  float core = exp(-across * across * 22.0);
  float sheath = exp(-across * across * 3.5) * 0.28;
  float flow = pow(0.5 + 0.5 * sin(along * uLen * 0.8 - uTime * 5.0), 8.0);
  float ends = smoothstep(0.0, 0.04, along);
  float head = uHead < 0.999 ? exp(-pow((uHead - along) * uLen * 0.7, 2.0)) * 1.6 : 0.0;
  float i = ((core * (1.0 + flow * 0.9) + sheath) * ends + head * (core + sheath)) * uPower;
  gl_FragColor = vec4(uColor * i, 1.0);
}
`

/** A wave on the plane where a ray found its sign. */
const SHOCK_FRAG = /* glsl */ `
uniform vec3 uColor;
uniform float uT;
varying vec2 vUv;
void main() {
  float d = length(vUv - 0.5) * 2.0;
  float r = uT;
  float ring = exp(-pow((d - r) * 14.0, 2.0)) + 0.35 * exp(-pow((d - r * 0.7) * 8.0, 2.0));
  float a = ring * (1.0 - uT) * (1.0 - uT) * step(d, 1.0);
  gl_FragColor = vec4(uColor, a * 1.4);
}
`

/** Sparks flying out of a body; `uT` runs from 0 to 1. */
const BURST_VERT = /* glsl */ `
attribute vec3 dir;
attribute float speed;
uniform vec3 uOrigin;
uniform float uT;
uniform float uDpr;
varying float vA;
void main() {
  float e = 1.0 - pow(1.0 - uT, 3.0);
  vec3 p = uOrigin + dir * speed * e * 3.2;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  vA = (1.0 - uT) * step(0.0001, uT);
  gl_PointSize = (2.0 + speed * 2.5) * uDpr * (1.0 - uT * 0.6);
}
`
const BURST_FRAG = /* glsl */ `
uniform vec3 uColor;
varying float vA;
void main() {
  float d = length(gl_PointCoord - 0.5) * 2.0;
  gl_FragColor = vec4(uColor, exp(-d * d * 5.0) * vA * step(d, 1.0));
}
`

/* ---- What the bodies look like (not to scale) ---- */

export const LOOKS = {
  sun: { radius: 1.8 },
  mercury: { radius: 0.36, kind: 0, a: 0x8d8379, b: 0xbdb3a7, c: 0x5e5750, rim: 0xd8cfc3, seed: 3.1 },
  venus: { radius: 0.55, kind: 1, a: 0xe2c48a, b: 0xf3dfb4, c: 0xc99f5c, rim: 0xffe0a0, bands: 5, seed: 7.4 },
  earth: { radius: EARTH_RADIUS, kind: 2, a: 0x1d4f8f, b: 0x4f7d3c, c: 0xffffff, rim: 0x86bcff, seed: 2.2 },
  moon: { radius: 0.2, kind: 0, a: 0x8f8d89, b: 0xd2cdc5, c: 0x66635f, rim: 0xe8e4dc, seed: 11.3 },
  mars: { radius: 0.45, kind: 0, a: 0xa84b26, b: 0xdd8048, c: 0x6e2c14, rim: 0xff9e6e, seed: 5.6 },
  jupiter: { radius: 1.2, kind: 1, a: 0xc59e76, b: 0xf0e2c8, c: 0x9a6640, rim: 0xffd9a8, bands: 15, seed: 1.7 },
  saturn: { radius: 1.0, kind: 1, a: 0xd8bf88, b: 0xf2e4bc, c: 0xae8b52, rim: 0xffe6b0, bands: 12, seed: 4.9 },
  uranus: { radius: 0.75, kind: 1, a: 0x9bd6dc, b: 0xc8f0f2, c: 0x83c0c8, rim: 0xbff6ff, bands: 4, seed: 8.8 },
  neptune: { radius: 0.72, kind: 1, a: 0x3c6dd4, b: 0x5d8ef1, c: 0x274ca5, rim: 0x94b6ff, bands: 6, seed: 6.2 },
  pluto: { radius: 0.28, kind: 0, a: 0xb19880, b: 0xdcc8b1, c: 0x7b6856, rim: 0xeedcc8, seed: 9.5 },
}

/** The constellations stand behind the belt, each in a box this large, its foot this high. */
export const FIGURE = { radius: 47, size: 11, foot: 1.4 }

function glyphAtlas(serif) {
  const cell = { w: 256, h: 200 }
  const canvas = document.createElement('canvas')
  canvas.width = cell.w * 4
  canvas.height = cell.h * 3
  const ctx = canvas.getContext('2d')
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.shadowColor = 'rgba(255, 196, 110, 0.55)'
  ctx.shadowBlur = 14
  SIGN_LIST.forEach((sign, index) => {
    const x = (index % 4) * cell.w + cell.w / 2
    const y = Math.floor(index / 4) * cell.h
    ctx.fillStyle = '#ffe9c2'
    ctx.font = `104px ${serif}`
    ctx.fillText(sign.glyph, x, y + 84)
    ctx.fillStyle = 'rgba(255, 233, 194, 0.88)'
    ctx.font = `600 30px ${serif}`
    ctx.fillText(sign.name.toLocaleUpperCase('ru').split('').join(' '), x, y + 168)
  })
  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  texture.anisotropy = 4
  return { texture, cell: { u: 1 / 4, v: 1 / 3 } }
}

/** The polylines of an engraving and the stick figure, as segments in the figure's own frame (x right, y up). */
function figureLines(id, size, lite) {
  const art = []
  for (const stroke of ZODIAC_ART[id] || []) {
    if (lite && stroke.kind === 'hatch') continue
    const pts = stroke.pts
    for (let i = 1; i < pts.length; i += 1) {
      art.push(
        (pts[i - 1][0] / 1000 - 0.5) * size, -(pts[i - 1][1] / 1000 - 0.5) * size, 0,
        (pts[i][0] / 1000 - 0.5) * size, -(pts[i][1] / 1000 - 0.5) * size, 0,
      )
    }
  }
  const stars = PROJECTED[id]
  const edges = []
  for (const [a, b] of ZODIAC_BY_ID[id].edges) {
    edges.push(stars[a].x * size, -stars[a].y * size, 0.02, stars[b].x * size, -stars[b].y * size, 0.02)
  }
  let low = Math.min(...stars.map((p) => -p.y * size))
  for (let i = 1; i < art.length; i += 3) low = Math.min(low, art[i])
  return { art: new Float32Array(art), edges: new Float32Array(edges), low }
}

function lineMaterial(color, alpha) {
  return new ShaderMaterial({
    uniforms: { uColor: { value: vec3(color) }, uAlpha: { value: alpha } },
    vertexShader: LINE_VERT,
    fragmentShader: LINE_FRAG,
    ...GLOW,
  })
}

/**
 * Builds the scene on `canvas`. `lite`: the phone's lighter sky — fewer stars, no hatching in the
 * engravings, coarser spheres, no antialiasing. Returns null when WebGL is not there.
 */
export function createScene(canvas, { lite = false, onLost = () => {} } = {}) {
  let renderer
  try {
    renderer = new WebGLRenderer({ canvas, antialias: !lite, alpha: true, powerPreference: lite ? 'default' : 'high-performance' })
  } catch {
    return null
  }
  renderer.setClearColor(0x000000, 0)
  const lost = (event) => {
    event.preventDefault()
    onLost()
  }
  canvas.addEventListener('webglcontextlost', lost)

  const scene = new Scene()
  const camera = new PerspectiveCamera(38, 1, 0.5, 3000)
  const view = { az: -90, el: 56, dist: 140, cx: 0, cy: 0, lx: 0, ly: 0 }
  const size = { W: 1, H: 1, dpr: 1 }
  const billboards = []
  const disposables = []
  const keep = (thing) => {
    disposables.push(thing)
    return thing
  }
  const serif = getComputedStyle(document.documentElement).getPropertyValue('--serif').trim() || 'Georgia, serif'

  /* ---- The background stars ---- */

  const skyCount = lite ? 700 : 2200
  const skyPos = new Float32Array(skyCount * 3)
  const skySize = new Float32Array(skyCount)
  const skyPhase = new Float32Array(skyCount)
  const skyTint = new Float32Array(skyCount * 3)
  const band = new Matrix4().makeRotationX(62 * RAD).multiply(new Matrix4().makeRotationZ(20 * RAD))
  const v = new Vector3()
  for (let i = 0; i < skyCount; i += 1) {
    // Some of them gather in a band across the sky, a hint of the Milky Way.
    if (i % 5 < 2) {
      const a = Math.random() * TAU
      const spread = (Math.random() + Math.random() + Math.random() - 1.5) * 0.22
      v.set(Math.cos(a), spread, Math.sin(a)).normalize().applyMatrix4(band)
    } else {
      const u = Math.random() * 2 - 1
      const a = Math.random() * TAU
      const s = Math.sqrt(1 - u * u)
      v.set(s * Math.cos(a), u, s * Math.sin(a))
    }
    v.multiplyScalar(900)
    skyPos.set([v.x, v.y, v.z], i * 3)
    const bright = Math.random() ** 6
    skySize[i] = 1.1 + bright * 3.4
    skyPhase[i] = Math.random()
    const warm = Math.random()
    skyTint.set(warm < 0.2 ? [1, 0.86, 0.7] : warm > 0.85 ? [0.78, 0.86, 1] : [1, 0.97, 0.92], i * 3)
  }
  const skyGeo = keep(new BufferGeometry())
  skyGeo.setAttribute('position', new BufferAttribute(skyPos, 3))
  skyGeo.setAttribute('size', new BufferAttribute(skySize, 1))
  skyGeo.setAttribute('phase', new BufferAttribute(skyPhase, 1))
  skyGeo.setAttribute('tint', new BufferAttribute(skyTint, 3))
  const skyMat = keep(new ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uDpr: { value: 1 }, uAlpha: { value: 1 } },
    vertexShader: SKY_VERT,
    fragmentShader: SKY_FRAG,
    ...GLOW,
  }))
  const sky = new Points(skyGeo, skyMat)
  sky.frustumCulled = false
  scene.add(sky)

  /* ---- Glows ---- */

  const quad = keep(new PlaneGeometry(1, 1))
  function glow(color, scale, { sharp = 2.2, alpha = 1, ring = 0 } = {}) {
    const material = keep(new ShaderMaterial({
      uniforms: { uColor: { value: vec3(color) }, uAlpha: { value: alpha }, uSharp: { value: sharp }, uRing: { value: ring } },
      vertexShader: BILLBOARD_VERT,
      fragmentShader: GLOW_FRAG,
      ...GLOW,
    }))
    const mesh = new Mesh(quad, material)
    mesh.scale.setScalar(scale)
    mesh.renderOrder = 5
    billboards.push(mesh)
    scene.add(mesh)
    return mesh
  }

  /* ---- The bodies ---- */

  const sphere = keep(new SphereGeometry(1, lite ? 32 : 56, lite ? 20 : 36))
  const bodies = {}

  const sunMat = keep(new ShaderMaterial({ uniforms: { uTime: { value: 0 } }, vertexShader: SUN_VERT, fragmentShader: SUN_FRAG }))
  const sunMesh = new Mesh(sphere, sunMat)
  sunMesh.scale.setScalar(LOOKS.sun.radius)
  scene.add(sunMesh)
  const coronaMat = keep(new ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uAlpha: { value: 1 } },
    vertexShader: BILLBOARD_VERT,
    fragmentShader: CORONA_FRAG,
    ...GLOW,
  }))
  const corona = new Mesh(quad, coronaMat)
  corona.scale.setScalar(16)
  corona.renderOrder = 4
  billboards.push(corona)
  scene.add(corona)
  bodies.sun = { mesh: sunMesh, halo: corona, radius: LOOKS.sun.radius, xy: [0, 0], scale: 1 }

  for (const [id, look] of Object.entries(LOOKS)) {
    if (id === 'sun') continue
    const material = keep(new ShaderMaterial({
      uniforms: {
        uA: { value: vec3(look.a) },
        uB: { value: vec3(look.b) },
        uC: { value: vec3(look.c) },
        uRim: { value: vec3(look.rim) },
        uSun: { value: new Vector3() },
        uKind: { value: look.kind },
        uBands: { value: look.bands || 0 },
        uSeed: { value: look.seed },
        uSelf: { value: 0 },
        uTime: { value: 0 },
      },
      vertexShader: PLANET_VERT,
      fragmentShader: PLANET_FRAG,
    }))
    const mesh = new Mesh(sphere, material)
    mesh.scale.setScalar(look.radius)
    // A slight tilt of the axis, so the bands and the poles read as a globe; the spin (setSpin)
    // turns the globe about its own tilted axis.
    mesh.rotation.order = 'ZYX'
    mesh.rotation.z = (id === 'uranus' ? 82 : id === 'earth' ? 23 : 8) * RAD
    scene.add(mesh)
    const halo = glow(look.rim, Math.max(2.2, look.radius * 6), { sharp: 2.6, alpha: 0.35 })
    bodies[id] = { mesh, halo, radius: look.radius, xy: [0, 0], scale: 1 }
  }

  const ringInner = 1.35
  const ringOuter = 2.3
  const ringsGeo = keep(new RingGeometry(ringInner, ringOuter, lite ? 64 : 128, 1))
  const ringsMat = keep(new ShaderMaterial({
    uniforms: { uColor: { value: vec3(0xe8d2a0) }, uAlpha: { value: 1 }, uInner: { value: ringInner }, uOuter: { value: ringOuter } },
    vertexShader: RINGS_VERT,
    fragmentShader: RINGS_FRAG,
    transparent: true,
    depthWrite: false,
    side: DoubleSide,
  }))
  const rings = new Mesh(ringsGeo, ringsMat)
  rings.rotation.x = -Math.PI / 2 + 27 * RAD
  rings.renderOrder = 3
  scene.add(rings)

  // The birthplace on the Earth, and a ghost of where the body is wanted (on a hint).
  const marker = glow(0xfff4dc, 0.9, { sharp: 1.6, alpha: 0 })
  const ghost = glow(GOLD, 2.4, { ring: 0.62, alpha: 0 })

  /* ---- Orbits ---- */

  const circle = (() => {
    const n = 256
    const pts = new Float32Array(n * 3)
    for (let i = 0; i < n; i += 1) pts.set([Math.cos((i / n) * TAU), 0, -Math.sin((i / n) * TAU)], i * 3)
    const geo = keep(new BufferGeometry())
    geo.setAttribute('position', new BufferAttribute(pts, 3))
    return geo
  })()
  const orbits = {}
  for (const [id, r] of Object.entries(ORBITS)) {
    const material = keep(lineMaterial(0xc9d4ff, 0.14))
    const loop = new LineLoop(circle, material)
    loop.scale.setScalar(r)
    loop.renderOrder = 1
    scene.add(loop)
    orbits[id] = loop
  }
  const moonOrbit = new LineLoop(circle, keep(lineMaterial(0xc9d4ff, 0.12)))
  moonOrbit.scale.setScalar(MOON_ORBIT)
  moonOrbit.renderOrder = 1
  scene.add(moonOrbit)
  orbits.moon = moonOrbit

  /* ---- The belt and its glyphs ---- */

  const beltGeo = keep(new RingGeometry(BELT.inner, BELT.outer, lite ? 360 : 720, 1))
  const beltMat = keep(new ShaderMaterial({
    uniforms: {
      uLit: { value: new Array(12).fill(0) },
      uTarget: { value: -1 },
      uPulse: { value: 0 },
      uHit: { value: new Vector2(0, 0) },
      uTime: { value: 0 },
      uFade: { value: 1 },
      uGold: { value: vec3(GOLD) },
      uInner: { value: BELT.inner },
      uOuter: { value: BELT.outer },
    },
    vertexShader: BELT_VERT,
    fragmentShader: BELT_FRAG,
    ...GLOW,
    side: DoubleSide,
  }))
  const belt = new Mesh(beltGeo, beltMat)
  belt.rotation.x = -Math.PI / 2
  belt.renderOrder = 1
  scene.add(belt)

  const atlas = glyphAtlas(serif)
  keep(atlas.texture)
  const glyphs = SIGN_LIST.map((sign, index) => {
    const map = atlas.texture.clone()
    map.repeat.set(atlas.cell.u, atlas.cell.v)
    map.offset.set((index % 4) * atlas.cell.u, 1 - (Math.floor(index / 4) + 1) * atlas.cell.v)
    keep(map)
    const material = keep(new SpriteMaterial({ map, transparent: true, depthWrite: false, opacity: 0.6 }))
    const sprite = new Sprite(material)
    place(sprite.position, [Math.cos((index * 30 + 15) * RAD) * BELT.mid, Math.sin((index * 30 + 15) * RAD) * BELT.mid], 0.6)
    sprite.scale.set(4.1, 3.2, 1)
    sprite.renderOrder = 7
    scene.add(sprite)
    return sprite
  })

  /* ---- The constellations ---- */

  const figures = SIGN_LIST.map((sign, index) => {
    const lon = (index * 30 + 15) * RAD
    const stars = PROJECTED[sign.id]
    const { art, edges, low } = figureLines(sign.id, FIGURE.size, lite)
    // The figure's lowest stroke rests at the foot.
    const center = new Vector3(Math.cos(lon) * FIGURE.radius, FIGURE.foot - low, -Math.sin(lon) * FIGURE.radius)
    const group = new Group()
    const right = new Vector3(Math.sin(lon), 0, Math.cos(lon))
    const up = new Vector3(0, 1, 0)
    const inward = new Vector3(-Math.cos(lon), 0, Math.sin(lon))
    group.matrixAutoUpdate = false
    group.matrix.makeBasis(right, up, inward).setPosition(center)

    const artGeo = keep(new BufferGeometry())
    artGeo.setAttribute('position', new BufferAttribute(art, 3))
    const artMat = keep(lineMaterial(0xe9cf98, 0.1))
    const artLines = new LineSegments(artGeo, artMat)
    artLines.renderOrder = 2
    group.add(artLines)

    const edgeGeo = keep(new BufferGeometry())
    edgeGeo.setAttribute('position', new BufferAttribute(edges, 3))
    const edgeMat = keep(lineMaterial(0xfff1d6, 0.18))
    const edgeLines = new LineSegments(edgeGeo, edgeMat)
    edgeLines.renderOrder = 2
    group.add(edgeLines)

    const figure = ZODIAC_BY_ID[sign.id]
    const pos = new Float32Array(stars.length * 3)
    const sizes = new Float32Array(stars.length)
    const order = new Float32Array(stars.length)
    // The brightest star lights first.
    const ranked = figure.stars.map((star, i) => [star.mag, i]).sort((a, b) => a[0] - b[0])
    ranked.forEach(([, i], rank) => {
      order[i] = rank / Math.max(1, stars.length - 1)
    })
    stars.forEach((p, i) => {
      pos.set([p.x * FIGURE.size, -p.y * FIGURE.size, 0.04], i * 3)
      sizes[i] = Math.min(Math.max(2.4 + (4.6 - figure.stars[i].mag) * 1.5, 2.2), 8)
    })
    const starGeo = keep(new BufferGeometry())
    starGeo.setAttribute('position', new BufferAttribute(pos, 3))
    starGeo.setAttribute('size', new BufferAttribute(sizes, 1))
    starGeo.setAttribute('order', new BufferAttribute(order, 1))
    const starMat = keep(new ShaderMaterial({
      uniforms: {
        uDpr: { value: 1 },
        uLight: { value: 0 },
        uPop: { value: 1 },
        uTime: { value: 0 },
        uAlpha: { value: 1 },
        uColor: { value: vec3(0xfff4e0) },
      },
      vertexShader: STAR_VERT,
      fragmentShader: STAR_FRAG,
      ...GLOW,
    }))
    const points = new Points(starGeo, starMat)
    points.renderOrder = 3
    group.add(points)
    scene.add(group)
    return { group, center, inward, artMat, edgeMat, starMat, light: 0, pop: 1, show: 1 }
  })

  /* ---- Rays, waves and sparks ---- */

  const beams = Array.from({ length: 12 }, () => {
    const geo = keep(new BufferGeometry())
    geo.setAttribute('position', new BufferAttribute(new Float32Array(12), 3))
    geo.setAttribute('uv', new BufferAttribute(new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]), 2))
    geo.setIndex([0, 2, 1, 2, 3, 1])
    const material = keep(new ShaderMaterial({
      uniforms: {
        uColor: { value: vec3(GOLD) },
        uPower: { value: 1 },
        uLen: { value: 10 },
        uHead: { value: 1 },
        uTime: { value: 0 },
      },
      vertexShader: BILLBOARD_VERT,
      fragmentShader: BEAM_FRAG,
      ...GLOW,
      side: DoubleSide,
    }))
    const mesh = new Mesh(geo, material)
    mesh.frustumCulled = false
    mesh.renderOrder = 6
    mesh.visible = false
    scene.add(mesh)
    return { mesh, a: new Vector3(), b: new Vector3(), width: 0.5 }
  })

  const shocks = Array.from({ length: 3 }, () => {
    const material = keep(new ShaderMaterial({
      uniforms: { uColor: { value: vec3(PALE) }, uT: { value: 1 } },
      vertexShader: BILLBOARD_VERT,
      fragmentShader: SHOCK_FRAG,
      ...GLOW,
      side: DoubleSide,
    }))
    const mesh = new Mesh(quad, material)
    mesh.rotation.x = -Math.PI / 2
    mesh.renderOrder = 6
    mesh.visible = false
    scene.add(mesh)
    return { mesh, start: -1, duration: 1.4 }
  })

  const sparkCount = lite ? 40 : 80
  const bursts = Array.from({ length: 3 }, () => {
    const dirs = new Float32Array(sparkCount * 3)
    const speeds = new Float32Array(sparkCount)
    for (let i = 0; i < sparkCount; i += 1) {
      const u = Math.random() * 2 - 1
      const a = Math.random() * TAU
      const s = Math.sqrt(1 - u * u)
      // Flattened toward the plane: the sparks spread along the ecliptic more than across it.
      dirs.set([s * Math.cos(a), u * 0.45, s * Math.sin(a)], i * 3)
      speeds[i] = 0.3 + Math.random() * 0.9
    }
    const geo = keep(new BufferGeometry())
    geo.setAttribute('position', new BufferAttribute(new Float32Array(sparkCount * 3), 3))
    geo.setAttribute('dir', new BufferAttribute(dirs, 3))
    geo.setAttribute('speed', new BufferAttribute(speeds, 1))
    const material = keep(new ShaderMaterial({
      uniforms: { uOrigin: { value: new Vector3() }, uT: { value: 0 }, uDpr: { value: 1 }, uColor: { value: vec3(PALE) } },
      vertexShader: BURST_VERT,
      fragmentShader: BURST_FRAG,
      ...GLOW,
    }))
    const points = new Points(geo, material)
    points.frustumCulled = false
    points.renderOrder = 6
    points.visible = false
    scene.add(points)
    return { points, start: -1, duration: 1.1 }
  })

  /* ---- The camera ---- */

  const look = new Vector3()
  /** The camera at azimuth `az` and elevation `el` (degrees), `dist` from the point it looks at, (lx, ly). */
  function aim(target, { az, el, dist, lx = 0, ly = 0 }) {
    const a = az * RAD
    place(look, [lx, ly], 0)
    if (el >= 89.5) {
      // Straight down: the far side (az + 180°) is the top of the screen, as it was on the way up.
      target.position.set(look.x, dist, look.z)
      target.up.set(-Math.cos(a), 0, Math.sin(a))
    } else {
      const e = el * RAD
      target.position.set(look.x + dist * Math.cos(e) * Math.cos(a), dist * Math.sin(e), look.z - dist * Math.cos(e) * Math.sin(a))
      target.up.set(0, 1, 0)
    }
    target.lookAt(look)
    target.updateMatrixWorld()
  }

  /** The window of the canvas the system should fill, centred at (cx, cy): the HUD takes the rest. */
  function frame() {
    const { W, H } = size
    camera.aspect = W / H
    camera.setViewOffset(W, H, W / 2 - view.cx, H / 2 - view.cy, W, H)
    camera.updateProjectionMatrix()
  }

  /** The whole system seen from azimuth `az`: the belt, and the constellations standing on its far side. */
  function systemPoints(az) {
    const list = []
    for (let i = 0; i < 32; i += 1) list.push([...toward((i / 32) * 360, BELT.outer + 1.5), 0])
    for (let deg = -80; deg <= 80; deg += 20) list.push([...toward(az + 180 + deg, FIGURE.radius), FIGURE.foot + FIGURE.size])
    return list
  }

  /**
   * The distance at which `points` ([x, y, h]; the whole system by default) fill a box of w × h px
   * with the camera at `az`, `el`, looking at (lx, ly): found by halving, from the projection itself.
   */
  const probe = new PerspectiveCamera(camera.fov, 1, 0.5, 3000)
  function fit({ az = 0, el, lx = 0, ly = 0, points = null, w, h }) {
    const focal = size.H / 2 / Math.tan((probe.fov / 2) * RAD)
    const list = (points || systemPoints(az)).map(([x, y, height]) => place(new Vector3(), [x, y], height))
    const p = new Vector3()
    const fits = (dist) => {
      aim(probe, { az, el, dist, lx, ly })
      return list.every((point) => {
        p.copy(point).applyMatrix4(probe.matrixWorldInverse)
        if (p.z > -1) return false
        return Math.abs((p.x / -p.z) * focal) <= w / 2 && Math.abs((p.y / -p.z) * focal) <= h / 2
      })
    }
    let lo = 4
    let hi = 1200
    for (let i = 0; i < 26; i += 1) {
      const mid = (lo + hi) / 2
      if (fits(mid)) hi = mid
      else lo = mid
    }
    return hi
  }

  /** The distance straight above at which the belt's outer edge is `r` px from the centre: the wheel's size. */
  function wheelDistance(r) {
    const focal = size.H / 2 / Math.tan((camera.fov / 2) * RAD)
    return (focal * BELT.outer) / r
  }

  /* ---- The frame ---- */

  const tmp = new Vector3()
  const tmp2 = new Vector3()
  const side = new Vector3()
  const sunPos = new Vector3()
  let time = 0

  function updateBeam(beam) {
    const { mesh, a, b, width } = beam
    const pos = mesh.geometry.attributes.position
    tmp.subVectors(b, a)
    const len = tmp.length()
    tmp2.addVectors(a, b).multiplyScalar(0.5).sub(camera.position).negate()
    side.crossVectors(tmp, tmp2).normalize().multiplyScalar(width / 2)
    pos.setXYZ(0, a.x - side.x, a.y - side.y, a.z - side.z)
    pos.setXYZ(1, b.x - side.x, b.y - side.y, b.z - side.z)
    pos.setXYZ(2, a.x + side.x, a.y + side.y, a.z + side.z)
    pos.setXYZ(3, b.x + side.x, b.y + side.y, b.z + side.z)
    pos.needsUpdate = true
    mesh.material.uniforms.uLen.value = len
    mesh.material.uniforms.uTime.value = time
  }

  function render(seconds) {
    time = seconds
    aim(camera, view)
    frame()
    sunMat.uniforms.uTime.value = seconds
    coronaMat.uniforms.uTime.value = seconds
    skyMat.uniforms.uTime.value = seconds
    beltMat.uniforms.uTime.value = seconds
    sunPos.copy(bodies.sun.mesh.position)
    for (const [id, body] of Object.entries(bodies)) {
      if (id === 'sun') continue
      body.mesh.material.uniforms.uSun.value.copy(sunPos)
      body.mesh.material.uniforms.uTime.value = seconds
    }
    for (const mesh of billboards) mesh.quaternion.copy(camera.quaternion)
    for (const beam of beams) if (beam.mesh.visible) updateBeam(beam)

    // A constellation seen from behind (the near side of the belt) steps back, unless it is lit.
    for (const figure of figures) {
      tmp.subVectors(camera.position, figure.center).normalize()
      const facing = Math.min(1, Math.max(0, (tmp.dot(figure.inward) + 0.05) / 0.4))
      const shown = figure.show * Math.max(facing, figure.light * 0.35)
      const light = figure.light
      figure.artMat.uniforms.uAlpha.value = shown * (0.09 + light * 0.42)
      figure.edgeMat.uniforms.uAlpha.value = shown * (0.16 + light * 0.5)
      figure.starMat.uniforms.uAlpha.value = shown
      figure.starMat.uniforms.uLight.value = light
      figure.starMat.uniforms.uPop.value = figure.pop
      figure.starMat.uniforms.uTime.value = seconds
      figure.group.visible = shown > 0.01
    }

    for (const shock of shocks) {
      if (!shock.mesh.visible) continue
      const t = (seconds - shock.start) / shock.duration
      if (t >= 1) shock.mesh.visible = false
      else shock.mesh.material.uniforms.uT.value = t
    }
    for (const burst of bursts) {
      if (!burst.points.visible) continue
      const t = (seconds - burst.start) / burst.duration
      if (t >= 1) burst.points.visible = false
      else burst.points.material.uniforms.uT.value = t
    }
    renderer.render(scene, camera)
  }

  function resize(W, H, dpr) {
    Object.assign(size, { W, H, dpr })
    renderer.setPixelRatio(dpr)
    renderer.setSize(W, H, false)
    skyMat.uniforms.uDpr.value = dpr
    for (const figure of figures) figure.starMat.uniforms.uDpr.value = dpr
    for (const burst of bursts) burst.points.material.uniforms.uDpr.value = dpr
    frame()
  }

  /* ---- What the game sets ---- */

  function setBody(id, xy, { scale = 1, glow: lit = 0, alpha = 1, h = 0 } = {}) {
    const body = bodies[id]
    body.xy = xy
    body.scale = scale
    place(body.mesh.position, xy, h)
    body.mesh.scale.setScalar(body.radius * scale)
    body.mesh.visible = alpha > 0.02 && scale > 0.01
    body.halo.position.copy(body.mesh.position)
    if (id === 'sun') {
      body.halo.scale.setScalar(16 * scale * (1 + lit * 0.15))
      coronaMat.uniforms.uAlpha.value = alpha
    } else {
      const base = Math.max(2.2, body.radius * 6) * scale
      body.halo.scale.setScalar(base * (1 + lit * 0.7))
      body.halo.material.uniforms.uAlpha.value = (0.3 + lit * 0.5) * alpha
      body.mesh.material.uniforms.uSelf.value = lit
    }
    if (id === 'saturn') {
      rings.position.copy(body.mesh.position)
      rings.scale.setScalar(scale)
      rings.visible = body.mesh.visible
    }
    if (id === 'earth') moonOrbit.position.copy(body.mesh.position)
  }

  function setSpin(id, deg) {
    bodies[id].mesh.rotation.y = deg * RAD
  }

  function setOrbit(id, { alpha = 0.14, gold = 0, radius = 0 } = {}) {
    const material = orbits[id].material
    if (radius) orbits[id].scale.setScalar(radius)
    material.uniforms.uColor.value.copy(tint(0xc9d4ff)).lerp(tint(GOLD), gold)
    material.uniforms.uAlpha.value = alpha
    orbits[id].visible = alpha > 0.005
  }

  function setMarker(xy, alpha = 1, h = 0) {
    marker.material.uniforms.uAlpha.value = xy ? alpha : 0
    if (xy) place(marker.position, xy, h)
  }

  function setGhost(xy, alpha = 1) {
    ghost.material.uniforms.uAlpha.value = xy ? alpha : 0
    if (xy) place(ghost.position, xy, 0)
  }

  /** The belt: `lit` per sector, the sector to pulse (−1 for none), where a ray lands and how bright. */
  function setBelt({ lit, target = -1, pulse = 0, hit = null, fade = 1, glyphs: glyphFade = 1, glyphLit = lit } = {}) {
    if (lit) for (let i = 0; i < 12; i += 1) beltMat.uniforms.uLit.value[i] = lit[i]
    beltMat.uniforms.uTarget.value = target
    beltMat.uniforms.uPulse.value = pulse
    beltMat.uniforms.uHit.value.set(hit ? hit[0] : 0, hit ? hit[1] : 0)
    beltMat.uniforms.uFade.value = fade
    belt.visible = fade > 0.005
    glyphs.forEach((sprite, i) => {
      const lift = glyphLit ? Math.min(1, glyphLit[i]) : 0
      const pulsing = i === target ? pulse * (0.5 + 0.5 * Math.sin(time * 3.2)) : 0
      sprite.material.opacity = glyphFade * (0.5 + lift * 0.5 + pulsing * 0.3)
      sprite.visible = glyphFade > 0.01
      const grow = 1 + lift * 0.18 + pulsing * 0.1
      sprite.scale.set(4.1 * grow, 3.2 * grow, 1)
    })
  }

  function setFigure(index, { light, pop, show } = {}) {
    const figure = figures[index]
    if (light !== undefined) figure.light = light
    if (pop !== undefined) figure.pop = pop
    if (show !== undefined) figure.show = show
  }

  /** Ray `k` from `from` to `to` (flat points, at the height of the plane). */
  function setBeam(k, from, to, { power = 1, color = GOLD, head = 1, width = 0.5, hFrom = 0 } = {}) {
    const beam = beams[k]
    if (!from || power <= 0.003) {
      beam.mesh.visible = false
      return
    }
    place(beam.a, from, hFrom)
    place(beam.b, to, 0)
    beam.width = width
    const u = beam.mesh.material.uniforms
    u.uPower.value = power
    u.uHead.value = head
    u.uColor.value.copy(tint(color))
    beam.mesh.visible = true
  }

  function shock(xy, { color = PALE, scale = 9, duration = 1.4 } = {}) {
    const free = shocks.find((item) => !item.mesh.visible) || shocks[0]
    place(free.mesh.position, xy, 0.05)
    free.mesh.scale.setScalar(scale)
    free.mesh.material.uniforms.uColor.value.copy(tint(color))
    free.mesh.material.uniforms.uT.value = 0
    free.start = time
    free.duration = duration
    free.mesh.visible = true
  }

  function burst(xy, { color = PALE, h = 0 } = {}) {
    const free = bursts.find((item) => !item.points.visible) || bursts[0]
    place(free.points.material.uniforms.uOrigin.value, xy, h)
    free.points.material.uniforms.uColor.value.copy(tint(color))
    free.points.material.uniforms.uT.value = 0
    free.start = time
    free.points.visible = true
  }

  function setSky(alpha) {
    skyMat.uniforms.uAlpha.value = alpha
  }

  /** Where a flat point is on the canvas, in CSS px. */
  function project(xy, h = 0) {
    place(tmp, xy, h).project(camera)
    return { x: ((tmp.x + 1) / 2) * size.W, y: ((1 - tmp.y) / 2) * size.H, front: tmp.z < 1 }
  }

  /** The flat point of the ecliptic under a point of the canvas (CSS px), or null above the horizon. */
  const raycaster = new Raycaster()
  const ground = new Plane(new Vector3(0, 1, 0), 0)
  const ndc = new Vector2()
  function groundAt(x, y) {
    ndc.set((x / size.W) * 2 - 1, -(y / size.H) * 2 + 1)
    raycaster.setFromCamera(ndc, camera)
    const hit = raycaster.ray.intersectPlane(ground, tmp)
    return hit ? [hit.x, -hit.z] : null
  }

  function dispose() {
    canvas.removeEventListener('webglcontextlost', lost)
    for (const thing of disposables) thing.dispose()
    renderer.dispose()
    renderer.forceContextLoss?.()
  }

  return {
    view,
    bodies,
    fit,
    wheelDistance,
    render,
    resize,
    setBody,
    setSpin,
    setOrbit,
    setMarker,
    setGhost,
    setBelt,
    setFigure,
    setBeam,
    setSky,
    shock,
    burst,
    project,
    groundAt,
    dispose,
  }
}
