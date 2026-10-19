export const VERTEX = `
attribute vec2 aPos;
void main() { gl_Position = vec4(aPos, 0.0, 1.0); }
`

/*
 * One pass for the whole backdrop: sky, nebulae, stars, planet, Sun and Moon.
 * Coordinates are CSS pixels with y down, sizes are reference pixels times uU.
 * The planet, Sun and Moon may be scaled down (uBodyU); the starry band pans by uPan.
 */
export const FRAGMENT = `
precision highp float;

uniform vec2 uRes;
uniform float uDpr;
uniform float uTime;
uniform float uU;
uniform float uBodyU;
uniform float uPan;
uniform float uBand2;
uniform vec2 uSun;
uniform vec2 uMoon;
uniform vec3 uPlanet;
uniform float uWarm;
uniform float uSunHover;
uniform float uMoonHover;
uniform float uIntro;
uniform float uHigh;

const vec3 GOLD = vec3(1.0, 0.66, 0.27);
const vec3 EMBER = vec3(0.95, 0.45, 0.14);
const vec3 ICE = vec3(0.36, 0.55, 0.95);

float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}

vec2 hash22(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.xx + p3.yz) * p3.zy);
}

float vnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 w = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash12(i), hash12(i + vec2(1.0, 0.0)), w.x),
    mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), w.x),
    w.y
  );
}

float fbm(vec2 p) {
  float sum = 0.0;
  float amp = 0.5;
  mat2 m = mat2(1.6, 1.2, -1.2, 1.6);
  for (int i = 0; i < 6; i++) {
    sum += amp * vnoise(p);
    p = m * p;
    amp *= 0.5;
  }
  return sum;
}

float fbm4(vec2 p) {
  float sum = 0.0;
  float amp = 0.5;
  mat2 m = mat2(1.6, 1.2, -1.2, 1.6);
  for (int i = 0; i < 4; i++) {
    sum += amp * vnoise(p);
    p = m * p;
    amp *= 0.5;
  }
  return sum;
}

// Ashima Arts 3D simplex noise (MIT).
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 1.0) * x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute(permute(permute(
    i.z + vec4(0.0, i1.z, i2.z, 1.0))
    + i.y + vec4(0.0, i1.y, i2.y, 1.0))
    + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

float starLayer(vec2 p, float cell, float density, float seed, float boost, out vec3 tint) {
  vec2 g = floor(p / cell);
  vec2 f = fract(p / cell);
  vec2 h = hash22(g + seed);
  float pick = hash12(g * 1.37 + seed * 7.1);
  float present = step(1.0 - density * boost, pick);
  vec2 d = (f - (0.15 + 0.7 * h)) * cell;
  float mag = hash12(g + seed * 3.3);
  float size = mix(0.55, 1.25, mag * mag);
  float tw = 0.72 + 0.28 * sin(uTime * (0.7 + 2.4 * h.x) + h.y * 40.0);
  float core = exp(-dot(d, d) / (size * size));
  tint = mix(vec3(1.0, 0.86, 0.7), vec3(0.75, 0.85, 1.0), h.y);
  return present * core * (0.3 + 0.9 * mag) * tw;
}

float brightStar(vec2 p, float cell, float density, float seed, out vec3 tint) {
  vec2 g = floor(p / cell);
  vec2 f = fract(p / cell);
  vec2 h = hash22(g + seed);
  float present = step(1.0 - density, hash12(g * 2.11 + seed));
  vec2 d = (f - (0.2 + 0.6 * h)) * cell;
  float tw = 0.65 + 0.35 * sin(uTime * (0.5 + 1.5 * h.y) + h.x * 30.0);
  float core = exp(-dot(d, d) / 1.6);
  float spikes = exp(-abs(d.x) * 1.4) * exp(-d.y * d.y / 70.0) + exp(-abs(d.y) * 1.4) * exp(-d.x * d.x / 70.0);
  float halo = exp(-length(d) / 5.0) * 0.25;
  tint = mix(vec3(1.0, 0.9, 0.75), vec3(0.8, 0.88, 1.0), h.x);
  return present * (core * 1.4 + spikes * 0.35 * tw + halo) * tw;
}

void main() {
  vec2 p = vec2(gl_FragCoord.x, uRes.y * uDpr - gl_FragCoord.y) / uDpr;
  vec2 uv = p / uRes;
  // Band coordinates: the stars travel with the zodiac, nebulae a little slower.
  vec2 sp = p - vec2(uPan, 0.0);
  vec2 s = (p - vec2(uPan * 0.6, 0.0)) / uU;
  float t = uTime;
  float warm = uWarm;

  vec2 pc = uPlanet.xy;
  float pr = uPlanet.z;
  vec2 dp = (p - pc) / pr;
  float rp = length(dp);
  float planetEdge = (rp - 1.0) * pr;
  float inPlanet = 1.0 - smoothstep(-0.8, 0.8, planetEdge);

  float sunAlt = (length(uSun - pc) - pr) / uBodyU;
  float moonAlt = (length(uMoon - pc) - pr) / uBodyU;
  float sunVis = smoothstep(-70.0, 30.0, sunAlt);
  float moonVis = smoothstep(-70.0, 30.0, moonAlt);

  // --- Sky base
  vec3 col = mix(vec3(0.006, 0.008, 0.02), vec3(0.016, 0.018, 0.034), smoothstep(0.0, 0.9, uv.y));
  col += vec3(0.05, 0.022, 0.008) * smoothstep(0.6, 0.0, uv.x) * smoothstep(0.1, 0.9, uv.y) * (0.4 + 0.8 * warm);
  col += vec3(0.004, 0.014, 0.045) * smoothstep(0.45, 1.0, uv.x) * (1.4 - 0.6 * warm);

  // --- Warm cloud bank (left), lit from the Sun
  vec2 w = s * 0.0042 + vec2(t * 0.0035, -t * 0.002);
  vec2 warp = vec2(fbm4(w * 1.4 + 7.3), fbm4(w * 1.4 + 2.1));
  float n = fbm(w + 1.6 * warp);
  float horizonBank = exp(-max(planetEdge / uBodyU - 40.0, 0.0) / 230.0) * (1.0 - inPlanet);
  float warmMask = smoothstep(0.5, 0.0, uv.x) * smoothstep(0.12, 0.85, uv.y) * 0.85;
  warmMask += horizonBank * smoothstep(0.5, 0.12, uv.x) * 0.9;
  warmMask = clamp(warmMask, 0.0, 1.0);
  float cloud = smoothstep(0.4, 0.82, n) * warmMask;
  float toSun = exp(-length(p - uSun) / (720.0 * uBodyU));
  float billow = smoothstep(0.45, 0.95, fbm4(w * 3.1 - warp * 1.2));
  vec3 cloudCol = mix(vec3(0.16, 0.06, 0.015), vec3(1.0, 0.56, 0.2), clamp(cloud * 1.25 + billow * 0.4, 0.0, 1.0));
  cloudCol = mix(cloudCol, vec3(1.0, 0.84, 0.58), billow * cloud * 0.7);
  float warmGain = (0.45 + 1.0 * warm) * (0.7 + 0.9 * toSun * sunVis) * (0.8 + horizonBank * 0.6);
  col += cloudCol * cloud * warmGain;
  col += EMBER * 0.06 * warmMask * n * warmGain;

  // --- Cool nebula and Milky Way (right)
  vec2 wc = s * 0.0036 + vec2(-t * 0.0028, t * 0.0015) + 19.0;
  float nc = fbm(wc + 1.2 * vec2(fbm4(wc * 1.7), fbm4(wc * 1.7 + 4.0)));
  float coolMask = smoothstep(0.55, 1.0, uv.x) * smoothstep(1.05, 0.1, uv.y) * 0.8;
  coolMask += horizonBank * smoothstep(0.55, 0.9, uv.x) * 0.9;
  coolMask = clamp(coolMask, 0.0, 1.0);
  vec2 bandDir = normalize(vec2(-0.55, 1.0));
  vec2 bandOrigin = vec2(uRes.x * 1.02, -uRes.y * 0.05);
  vec2 bandNormal = vec2(bandDir.y, -bandDir.x);
  float across = dot(sp - bandOrigin, bandNormal) / uU;
  // The Milky Way crosses the ecliptic twice: by Taurus and by Sagittarius.
  float across2 = dot(sp - vec2(uBand2, -uRes.y * 0.05), bandNormal) / uU;
  float band = max(exp(-across * across / (2.0 * 170.0 * 170.0)), exp(-across2 * across2 / (2.0 * 190.0 * 190.0)));
  band *= smoothstep(1.1, 0.2, uv.y);
  float lane = smoothstep(0.55, 0.75, fbm4(sp / uU * 0.012 + 5.0)) * band;
  float wisp = smoothstep(0.42, 0.9, nc);
  float coolGain = 0.45 + 0.85 * (1.0 - warm);
  vec3 coolCol = mix(vec3(0.03, 0.06, 0.16), vec3(0.4, 0.6, 1.0), wisp);
  col += coolCol * (wisp * coolMask * 0.9 + band * 0.28 * nc) * coolGain;
  col += vec3(0.55, 0.62, 0.8) * band * fbm4(sp / uU * 0.03) * 0.09 * coolGain;
  col *= 1.0 - lane * 0.45;

  // --- Stars
  float starKill = (1.0 - inPlanet) * (1.0 - clamp(cloud * warmGain * 1.6, 0.0, 0.9));
  vec3 tint;
  float bandBoost = 1.0 + band * 3.5;
  float starNight = 0.55 + 0.6 * (1.0 - warm);
  float st = starLayer(sp, 7.0, 0.05, 1.0, bandBoost, tint);
  col += tint * st * 0.55 * starNight * starKill;
  st = starLayer(sp, 17.0, 0.16, 11.0, 1.0 + band * 1.5, tint);
  col += tint * st * 0.9 * starNight * starKill;
  st = starLayer(sp, 37.0, 0.22, 29.0, 1.0, tint);
  col += tint * st * 1.15 * starNight * starKill;
  if (uHigh > 0.5) {
    st = brightStar(sp, 151.0, 0.32, 41.0, tint);
    col += tint * st * starNight * starKill;
  }

  // --- Sun light across the sky
  vec2 ds = (p - uSun) / uBodyU;
  float rs = length(ds);
  float sunScale = 1.0 + uSunHover * 0.07;
  float R0 = 35.0 * sunScale;
  vec3 sunLight = vec3(1.0, 0.64, 0.3);
  float sunGlow = exp(-rs / 40.0) * 0.95 + exp(-rs / 130.0) * 0.3 + exp(-rs / 480.0) * 0.08;
  col += sunLight * sunGlow * sunVis * (1.0 + uSunHover * 0.35) * (1.0 - inPlanet);

  // --- Moon light
  vec2 dm = (p - uMoon) / uBodyU;
  float rm = length(dm);
  float moonScale = 1.0 + uMoonHover * 0.07;
  float M0 = 33.0 * moonScale;
  float moonGlow = exp(-rm / 34.0) * 0.3 + exp(-rm / 150.0) * 0.1 + exp(-rm / 480.0) * 0.035;
  col += vec3(0.62, 0.74, 1.0) * moonGlow * moonVis * (1.0 + uMoonHover * 0.5) * (1.0 - inPlanet);

  // --- Planet atmosphere outside the limb
  vec2 limbDir = normalize(dp);
  vec2 sunDir = normalize(uSun - pc);
  vec2 moonDir = normalize(uMoon - pc);
  float sideSun = smoothstep(0.2, 1.0, dot(limbDir, sunDir));
  float sideMoon = smoothstep(0.2, 1.0, dot(limbDir, moonDir));
  float above = max(planetEdge / uBodyU, 0.0);
  float haze = exp(-above / 6.0) * 0.9 + exp(-above / 30.0) * 0.3 + exp(-above / 110.0) * 0.08;
  vec3 airWarm = mix(vec3(1.0, 0.7, 0.4), vec3(1.0, 0.9, 0.75), exp(-above / 6.0));
  vec3 airCool = mix(vec3(0.35, 0.55, 1.0), vec3(0.75, 0.85, 1.0), exp(-above / 6.0));
  vec3 air = airWarm * sideSun * (0.5 + warm) * (0.4 + 0.6 * sunVis) + airCool * sideMoon * (0.4 + 0.7 * (1.0 - warm));
  air += vec3(0.6, 0.62, 0.7) * 0.12 * exp(-above / 10.0);
  col += air * haze * (1.0 - inPlanet);

  // --- Planet surface
  if (rp < 1.0) {
    vec3 nrm = vec3(dp, sqrt(max(1.0 - rp * rp, 0.0)));
    float spin = t * 0.0035;
    float cs = cos(spin);
    float sn = sin(spin);
    vec3 q = vec3(nrm.x * cs - nrm.z * sn, nrm.y, nrm.x * sn + nrm.z * cs);
    vec3 L = normalize(vec3(sunDir * 0.9, 0.55));
    vec3 Lm = normalize(vec3(moonDir * 0.9, 0.55));
    float lit = clamp(dot(nrm, L), 0.0, 1.0) * sunVis;
    float litMoon = clamp(dot(nrm, Lm), 0.0, 1.0) * moonVis;

    vec3 tq = q * 7.0;
    float terrain = snoise(tq) * 0.55 + snoise(tq * 2.3 + 4.0) * 0.28 + snoise(tq * 5.1 + 9.0) * 0.17;
    float detail = uHigh > 0.5 ? snoise(tq * 11.0 + 2.0) * 0.5 + 0.5 : 0.5;
    float crater = smoothstep(0.55, 0.75, snoise(tq * 3.3 + 17.0)) * 0.35;
    vec3 rock = mix(vec3(0.04, 0.05, 0.075), vec3(0.17, 0.17, 0.19), terrain * 0.5 + 0.5);
    rock = mix(rock, vec3(0.32, 0.24, 0.15), smoothstep(0.15, 0.75, terrain) * 0.4 * (0.4 + warm));
    rock *= 0.82 + detail * 0.3 - crater;

    float v1 = 1.0 - abs(snoise(q * 11.0 + 3.0));
    float v2 = 1.0 - abs(snoise(q * 26.0 + 8.0));
    float v3 = 1.0 - abs(snoise(q * 57.0 + 1.0));
    float clusterMask = smoothstep(-0.35, 0.45, snoise(q * 4.0 + 21.0));
    float veinMask = smoothstep(-0.55, 0.35, snoise(q * 2.2 + 40.0));
    float vein = (pow(v1, 48.0) * 1.0 + pow(v2, 60.0) * 0.7 * clusterMask + pow(v3, 70.0) * 0.4 * clusterMask) * veinMask;
    float veinSoft = (pow(v1, 10.0) * 0.16 + pow(v2, 14.0) * 0.08 * clusterMask) * veinMask;
    float flicker = 0.85 + 0.15 * sin(t * 0.8 + q.x * 40.0 + q.y * 25.0);

    float light = 0.16 + lit * 1.05 + litMoon * 0.35;
    vec3 surf = rock * light * mix(vec3(0.75, 0.85, 1.1), vec3(1.15, 0.95, 0.75), lit);
    surf += rock * vec3(0.25, 0.35, 0.6) * litMoon * 0.5;
    float veinGain = (0.4 + 0.7 * warm) * (0.35 + 1.0 * lit + 0.25 * litMoon) * flicker;
    surf += GOLD * vein * veinGain * 1.25;
    surf += EMBER * veinSoft * veinGain * 0.8;

    float fres = pow(1.0 - nrm.z, 3.2);
    float rimSun = smoothstep(-0.2, 0.9, dot(normalize(dp), sunDir));
    float rimMoon = smoothstep(-0.2, 0.9, dot(normalize(dp), moonDir));
    surf += vec3(1.0, 0.62, 0.3) * fres * rimSun * (0.6 + 0.8 * warm) * (0.4 + 0.6 * sunVis);
    surf += vec3(0.35, 0.55, 1.0) * fres * rimMoon * (0.5 + 0.8 * (1.0 - warm));
    surf += vec3(0.9, 0.92, 1.0) * pow(1.0 - nrm.z, 14.0) * 0.5;

    col = mix(col, surf, inPlanet);
  }

  // --- Sun body
  if (sunVis > 0.0) {
    vec2 sd = vec2(cos(atan(ds.y, ds.x)), sin(atan(ds.y, ds.x)));
    float rays = vnoise(sd * 9.0 + vec2(t * 0.35, -t * 0.2)) * vnoise(sd * 21.0 - vec2(t * 0.5, t * 0.3) + 7.0);
    rays = pow(rays, 2.4) * 3.0;
    float rayFall = smoothstep(R0 * 0.85, R0 * 1.02, rs) * exp(-(rs - R0) / (18.0 * sunScale));
    float corona = exp(-max(rs - R0, 0.0) / 9.0) * 0.8;
    vec3 sunAdd = vec3(1.0, 0.76, 0.42) * (rays * rayFall * 1.6 + corona);
    float disc = 1.0 - smoothstep(R0 - 0.9 / uBodyU, R0 + 0.9 / uBodyU, rs);
    if (rs < R0 + 2.0) {
      vec2 sp = ds / R0;
      float mu = sqrt(max(1.0 - dot(sp, sp), 0.0));
      float gran = fbm4(sp * 6.0 / max(mu, 0.25) * 0.5 + t * 0.12) * 0.6 + fbm4(sp * 14.0 - t * 0.2) * 0.4;
      vec3 surface = mix(vec3(0.92, 0.36, 0.05), vec3(1.0, 0.78, 0.4), pow(mu, 0.7));
      surface = mix(surface, vec3(1.0, 0.93, 0.72), smoothstep(0.75, 1.0, mu) * 0.4);
      surface *= 0.78 + gran * 0.45;
      surface += vec3(1.0, 0.6, 0.2) * pow(1.0 - mu, 3.0) * 0.6;
      sunAdd = mix(sunAdd, surface * 1.15, disc);
    }
    float hide = 1.0 - inPlanet;
    col = mix(col, col * (1.0 - disc * hide) + sunAdd * hide, sunVis);
  }

  // --- Moon body
  if (moonVis > 0.0 && rm < M0 + 2.0) {
    vec2 mp = dm / M0;
    float mr = dot(mp, mp);
    vec3 mn = vec3(mp, sqrt(max(1.0 - mr, 0.0)));
    vec2 toSun = normalize(uSun - uMoon);
    vec3 ML = normalize(vec3(toSun, 0.45));
    float diff = dot(mn, ML);
    float terminator = smoothstep(-0.08, 0.22, diff);
    vec3 mq = vec3(mn.x, mn.y, mn.z) * 2.6;
    float maria = smoothstep(0.05, 0.55, snoise(mq * 0.9 + 3.0) * 0.6 + snoise(mq * 2.1) * 0.4);
    float pits = smoothstep(0.55, 0.85, snoise(mq * 4.5 + 11.0)) * 0.25 + smoothstep(0.62, 0.9, snoise(mq * 9.0 + 5.0)) * 0.2;
    float albedo = 0.86 - maria * 0.32 - pits * 0.6 + (snoise(mq * 18.0) * 0.06);
    vec3 moonSurf = vec3(0.86, 0.88, 0.92) * albedo;
    float limb = 0.65 + 0.35 * pow(mn.z, 0.5);
    vec3 earthshine = vec3(0.06, 0.08, 0.13) * albedo;
    vec3 moonCol = mix(earthshine, moonSurf * limb * (0.55 + 0.6 * max(diff, 0.0)), terminator);
    moonCol += vec3(0.6, 0.72, 1.0) * pow(1.0 - mn.z, 4.0) * 0.25 * terminator;
    float mdisc = (1.0 - smoothstep(M0 - 0.9 / uBodyU, M0 + 0.9 / uBodyU, rm)) * (1.0 - inPlanet);
    col = mix(col, moonCol * (1.0 + uMoonHover * 0.15), mdisc * moonVis);
  }

  // --- Finish
  vec2 vig = (uv - vec2(0.5, 0.45)) * vec2(1.0, 1.25);
  col *= 1.0 - 0.32 * smoothstep(0.25, 0.9, dot(vig, vig) * 2.2);
  col = 1.0 - exp(-col * 1.25);
  col *= uIntro;
  col += (hash12(p * uDpr + fract(t)) - 0.5) / 255.0;
  gl_FragColor = vec4(col, 1.0);
}
`
