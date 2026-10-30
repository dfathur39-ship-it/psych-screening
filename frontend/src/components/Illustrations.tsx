/**
 * Ilustrasi lokal (SVG) untuk seluruh situs. Semua orisinal, tanpa file gambar eksternal.
 * Tiga tokoh tetap muncul di banyak halaman agar situs punya identitas sendiri:
 *   Rani  : berhijab, suka membaca, hijau tua dan kuning
 *   Bima  : berkacamata, sering berpikir, oranye
 *   Sari  : rambut disanggul, teliti mengisi, hijau sage
 * Gaya: bentuk datar, tanpa garis tepi, wajah sederhana, warna pastel hangat.
 */
import type { ReactNode } from "react";

export const C = {
  cream: "#FAF7F0", beige: "#F0E9DC", sand: "#E6DCC8", sage: "#A8B8A0", sageDeep: "#7E9876",
  forest: "#354B3E", orange: "#D98B61", orangeSoft: "#EBB690", yellow: "#F0D58A", yellowSoft: "#F8E7B4",
  ink: "#30342F", blush: "#E39A86",
  skinRani: "#E7B28C", skinBima: "#C58B66", skinSari: "#F0C7A2",
  hairBima: "#2C2B29", hairSari: "#5B3F36",
};

/* ---------- potongan kecil ---------- */
type EyeMode = "open" | "closed" | "happy" | "down";
type MouthMode = "smile" | "calm" | "open";

function Face({ cx, cy, eyes = "open", mouth = "smile" }: { cx: number; cy: number; eyes?: EyeMode; mouth?: MouthMode }) {
  const ex = [cx - 9, cx + 9];
  return (
    <g>
      <circle cx={cx - 14} cy={cy + 8} r={4.6} fill={C.blush} opacity={0.5} />
      <circle cx={cx + 14} cy={cy + 8} r={4.6} fill={C.blush} opacity={0.5} />
      {ex.map((x) =>
        eyes === "open" ? <circle key={x} cx={x} cy={cy} r={2.7} fill={C.ink} /> :
        eyes === "closed" ? <path key={x} d={`M${x - 4} ${cy - 1} q4 4 8 0`} stroke={C.ink} strokeWidth={2.2} strokeLinecap="round" fill="none" /> :
        eyes === "happy" ? <path key={x} d={`M${x - 4} ${cy + 1.5} q4 -5.5 8 0`} stroke={C.ink} strokeWidth={2.2} strokeLinecap="round" fill="none" /> :
        <path key={x} d={`M${x - 4} ${cy + 1} h8`} stroke={C.ink} strokeWidth={2.2} strokeLinecap="round" fill="none" />
      )}
      {mouth === "smile" && <path d={`M${cx - 6} ${cy + 11} q6 6 12 0`} stroke={C.ink} strokeWidth={2.2} strokeLinecap="round" fill="none" />}
      {mouth === "calm" && <path d={`M${cx - 4} ${cy + 12} q4 3 8 0`} stroke={C.ink} strokeWidth={2.2} strokeLinecap="round" fill="none" />}
      {mouth === "open" && <path d={`M${cx - 7} ${cy + 10} q7 11 14 0z`} fill={C.ink} />}
    </g>
  );
}

const Limb = ({ d, color, w = 15 }: { d: string; color: string; w?: number }) => (
  <path d={d} stroke={color} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round" fill="none" />
);

export function Leaf({ x, y, r = 0, s = 1, fill = C.sage }: { x: number; y: number; r?: number; s?: number; fill?: string }) {
  return (
    <path transform={`translate(${x} ${y}) rotate(${r}) scale(${s})`} fill={fill}
      d="M0 0 C-26 -20 -30 -62 0 -96 C30 -62 26 -20 0 0Z" />
  );
}

export function Plant({ x, y, s = 1, tone = 0 }: { x: number; y: number; s?: number; tone?: number }) {
  const g = [C.sage, C.sageDeep, C.forest];
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <Leaf x={0} y={0} r={-48} s={0.85} fill={g[(tone + 0) % 3]} />
      <Leaf x={0} y={0} r={40} s={0.95} fill={g[(tone + 1) % 3]} />
      <Leaf x={0} y={0} r={-14} s={1.15} fill={g[(tone + 2) % 3]} />
      <Leaf x={0} y={0} r={16} s={0.8} fill={g[(tone + 0) % 3]} />
      <path d="M-24 0 H24 L18 40 H-18Z" fill={C.orange} />
      <rect x={-27} y={-6} width={54} height={10} rx={5} fill={C.orangeSoft} />
    </g>
  );
}

function Mug({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <path d="M0 0 h26 v20 a8 8 0 0 1 -8 8 h-10 a8 8 0 0 1 -8 -8z" fill="#fff" />
      <path d="M26 5 h4 a6 6 0 0 1 0 12 h-4" stroke="#fff" strokeWidth={4} fill="none" />
      <rect x={0} y={0} width={26} height={5} fill={C.yellow} />
    </g>
  );
}

/* ---------- tokoh dan pose (kotak 200 x 280, lantai di y = 270) ---------- */

/** Rani sedang membaca di kursi. */
export function RaniReading() {
  return (
    <g>
      {/* kursi */}
      <rect x={22} y={92} width={156} height={178} rx={44} fill={C.orange} />
      <rect x={34} y={200} width={132} height={70} rx={24} fill={C.orangeSoft} />
      <rect x={12} y={150} width={34} height={104} rx={17} fill={C.orange} />
      <rect x={154} y={150} width={34} height={104} rx={17} fill={C.orange} />
      {/* badan */}
      <path d="M66 270 C60 214 66 176 86 160 L114 160 C134 176 140 214 134 270Z" fill={C.yellow} />
      {/* kerudung */}
      <path d="M58 158 C52 112 70 74 100 74 C130 74 148 112 142 158 C130 146 118 142 100 142 C82 142 70 146 58 158Z" fill={C.forest} />
      <ellipse cx={100} cy={108} rx={21} ry={24} fill={C.skinRani} />
      <Face cx={100} cy={108} eyes="down" mouth="calm" />
      {/* buku */}
      <path d="M62 194 L100 204 L138 194 L138 242 L100 252 L62 242Z" fill={C.forest} />
      <path d="M66 190 L100 199 L100 247 L66 238Z" fill="#fff" />
      <path d="M134 190 L100 199 L100 247 L134 238Z" fill={C.cream} />
      <path d="M72 205 l22 5 M72 214 l22 5 M72 223 l22 5 M128 205 l-22 5 M128 214 l-22 5" stroke={C.sand} strokeWidth={2.4} strokeLinecap="round" />
      {/* lengan */}
      <Limb d="M80 166 Q58 200 70 232" color={C.yellow} w={17} />
      <Limb d="M120 166 Q142 200 130 232" color={C.yellow} w={17} />
      <circle cx={70} cy={236} r={8} fill={C.skinRani} />
      <circle cx={130} cy={236} r={8} fill={C.skinRani} />
    </g>
  );
}

/** Bima berdiri sambil berpikir. */
export function BimaThinking() {
  return (
    <g>
      <rect x={76} y={186} width={22} height={80} rx={11} fill={C.forest} />
      <rect x={102} y={186} width={22} height={80} rx={11} fill={C.forest} />
      <ellipse cx={86} cy={268} rx={15} ry={6.5} fill={C.ink} />
      <ellipse cx={114} cy={268} rx={15} ry={6.5} fill={C.ink} />
      <path d="M68 202 C62 164 66 142 86 132 L114 132 C134 142 138 164 132 202Z" fill={C.orange} />
      <rect x={93} y={118} width={14} height={18} rx={6} fill={C.skinBima} />
      <circle cx={100} cy={96} r={26} fill={C.skinBima} />
      <path d="M73 92 C72 66 90 64 102 64 C116 64 128 72 127 94 C122 84 112 80 100 80 C90 80 80 82 73 92Z" fill={C.hairBima} />
      <g stroke={C.ink} strokeWidth={2.3} fill="none">
        <circle cx={91} cy={98} r={7.5} /><circle cx={109} cy={98} r={7.5} /><path d="M98.500 98 h3" />
      </g>
      <Face cx={100} cy={98} eyes="open" mouth="calm" />
      {/* lengan kanan menopang, kiri ke dagu */}
      <Limb d="M127 146 Q140 178 108 182 L82 176" color={C.orange} />
      <Limb d="M74 146 Q58 170 74 174 Q90 168 96 128" color={C.orange} />
      <circle cx={97} cy={124} r={8} fill={C.skinBima} />
      <circle cx={80} cy={176} r={8} fill={C.skinBima} />
    </g>
  );
}

/** Sari duduk bersila mengisi kuesioner. */
export function SariForm() {
  return (
    <g>
      <ellipse cx={100} cy={250} rx={76} ry={26} fill={C.forest} />
      <ellipse cx={46} cy={254} rx={14} ry={9} fill={C.skinSari} />
      <ellipse cx={154} cy={254} rx={14} ry={9} fill={C.skinSari} />
      <path d="M64 242 C58 196 62 164 80 150 L120 150 C138 164 142 196 136 242Z" fill={C.sageDeep} />
      <rect x={93} y={128} width={14} height={20} rx={6} fill={C.skinSari} />
      <circle cx={100} cy={106} r={26} fill={C.skinSari} />
      <circle cx={100} cy={66} r={14} fill={C.hairSari} />
      <path d="M73 106 C70 78 88 74 100 74 C112 74 130 78 127 106 C119 94 110 90 100 90 C90 90 81 94 73 106Z" fill={C.hairSari} />
      <Face cx={100} cy={108} eyes="down" mouth="smile" />
      {/* papan jalan */}
      <rect x={66} y={182} width={68} height={56} rx={8} fill={C.orange} />
      <rect x={71} y={188} width={58} height={46} rx={4} fill="#fff" />
      <rect x={88} y={178} width={24} height={9} rx={4} fill={C.forest} />
      <g stroke={C.sage} strokeWidth={3} strokeLinecap="round" fill="none">
        <path d="M77 199 l3 3 l6 -6" stroke={C.sageDeep} /><path d="M92 199 h28" />
        <path d="M77 213 l3 3 l6 -6" stroke={C.sageDeep} /><path d="M92 213 h22" />
        <circle cx={80} cy={227} r={3.2} stroke={C.sage} /><path d="M92 227 h26" />
      </g>
      <Limb d="M80 160 Q60 194 88 214" color={C.sageDeep} w={16} />
      <Limb d="M120 160 Q142 190 120 206" color={C.sageDeep} w={16} />
      <circle cx={90} cy={217} r={8} fill={C.skinSari} />
      <circle cx={118} cy={208} r={8} fill={C.skinSari} />
      <path d="M118 208 l22 -26" stroke={C.yellow} strokeWidth={5} strokeLinecap="round" />
    </g>
  );
}

/** Sari beristirahat dengan secangkir teh. */
export function SariRest() {
  return (
    <g>
      <ellipse cx={100} cy={256} rx={92} ry={20} fill={C.orangeSoft} />
      <ellipse cx={100} cy={250} rx={80} ry={24} fill={C.forest} />
      <ellipse cx={50} cy={256} rx={14} ry={9} fill={C.skinSari} />
      <ellipse cx={150} cy={256} rx={14} ry={9} fill={C.skinSari} />
      <path d="M64 244 C58 198 62 166 80 152 L120 152 C138 166 142 198 136 244Z" fill={C.yellow} />
      <rect x={93} y={130} width={14} height={20} rx={6} fill={C.skinSari} />
      <circle cx={100} cy={108} r={26} fill={C.skinSari} />
      <circle cx={100} cy={68} r={14} fill={C.hairSari} />
      <path d="M73 108 C70 80 88 76 100 76 C112 76 130 80 127 108 C119 96 110 92 100 92 C90 92 81 96 73 108Z" fill={C.hairSari} />
      <Face cx={100} cy={110} eyes="closed" mouth="smile" />
      <Limb d="M80 164 Q62 196 92 206" color={C.yellow} w={16} />
      <Limb d="M120 164 Q138 196 108 206" color={C.yellow} w={16} />
      <Mug x={87} y={190} />
      <circle cx={92} cy={206} r={7.500} fill={C.skinSari} />
      <circle cx={108} cy={206} r={7.500} fill={C.skinSari} />
      <g stroke="#fff" strokeWidth={3} strokeLinecap="round" fill="none" opacity={0.9}>
        <path d="M94 180 q-6 -8 0 -14 q6 -6 0 -14" /><path d="M106 182 q6 -8 0 -14 q-6 -6 0 -14" />
      </g>
    </g>
  );
}

/** Rani berdiri riang, tangan terangkat. */
export function RaniHappy() {
  return (
    <g>
      <path d="M68 270 C62 210 66 170 86 158 L114 158 C134 170 138 210 132 270Z" fill={C.yellow} />
      <ellipse cx={86} cy={270} rx={14} ry={6} fill={C.ink} />
      <ellipse cx={114} cy={270} rx={14} ry={6} fill={C.ink} />
      <Limb d="M82 168 Q52 150 48 106" color={C.yellow} w={16} />
      <Limb d="M118 168 Q148 150 152 106" color={C.yellow} w={16} />
      <circle cx={48} cy={100} r={8} fill={C.skinRani} />
      <circle cx={152} cy={100} r={8} fill={C.skinRani} />
      <path d="M56 160 C50 112 68 72 100 72 C132 72 150 112 144 160 C132 148 118 144 100 144 C82 144 68 148 56 160Z" fill={C.forest} />
      <ellipse cx={100} cy={106} rx={21} ry={24} fill={C.skinRani} />
      <Face cx={100} cy={106} eyes="happy" mouth="open" />
    </g>
  );
}

/** Bima melambaikan tangan. */
export function BimaWave() {
  return (
    <g>
      <rect x={76} y={186} width={22} height={80} rx={11} fill={C.forest} />
      <rect x={102} y={186} width={22} height={80} rx={11} fill={C.forest} />
      <ellipse cx={86} cy={268} rx={15} ry={6.500} fill={C.ink} />
      <ellipse cx={114} cy={268} rx={15} ry={6.500} fill={C.ink} />
      <path d="M68 202 C62 164 66 142 86 132 L114 132 C134 142 138 164 132 202Z" fill={C.orange} />
      <rect x={93} y={118} width={14} height={18} rx={6} fill={C.skinBima} />
      <circle cx={100} cy={96} r={26} fill={C.skinBima} />
      <path d="M73 92 C72 66 90 64 102 64 C116 64 128 72 127 94 C122 84 112 80 100 80 C90 80 80 82 73 92Z" fill={C.hairBima} />
      <g stroke={C.ink} strokeWidth={2.300} fill="none">
        <circle cx={91} cy={98} r={7.500} /><circle cx={109} cy={98} r={7.500} /><path d="M98.500 98 h3" />
      </g>
      <Face cx={100} cy={98} eyes="open" mouth="smile" />
      <Limb d="M74 146 Q62 176 70 200" color={C.orange} />
      <Limb d="M127 146 Q158 140 158 98" color={C.orange} />
      <circle cx={70} cy={204} r={8} fill={C.skinBima} />
      <circle cx={158} cy={92} r={8.500} fill={C.skinBima} />
      <path d="M170 78 q8 8 0 18 M178 70 q12 14 0 30" stroke={C.orange} strokeWidth={3} strokeLinecap="round" fill="none" />
    </g>
  );
}

/* ---------- latar dan adegan ---------- */

export function Blob({ d, fill, ...rest }: { d: string; fill: string } & React.SVGProps<SVGPathElement>) {
  return <path d={d} fill={fill} {...rest} />;
}

const BLOB_A = "M300 30 C420 20 520 90 530 200 C540 310 460 410 330 420 C200 430 80 380 60 270 C40 160 150 40 300 30Z";
const BLOB_B = "M90 300 C70 220 140 170 220 190 C300 210 340 280 300 350 C260 420 110 400 90 300Z";

function Frame({ title, vb, children, className }: { title: string; vb: string; children: ReactNode; className?: string }) {
  return (
    <svg className={className} viewBox={vb} role="img" aria-label={title} xmlns="http://www.w3.org/2000/svg">
      {children}
    </svg>
  );
}

/** Adegan utama halaman depan: tiga tokoh, tiga suasana. */
export function HeroScene({ className }: { className?: string }) {
  return (
    <Frame className={className} vb="0 0 560 460" title="Tiga orang sedang membaca, berpikir, dan mengisi lembar jawaban di ruangan dengan tanaman">
      <Blob d={BLOB_A} fill={C.yellowSoft} />
      <Blob d={BLOB_B} fill={C.beige} transform="translate(180 20)" />
      <circle cx={448} cy={92} r={34} fill={C.yellow} />
      <ellipse cx={280} cy={432} rx={248} ry={16} fill={C.sand} />
      {/* rak dinding */}
      <rect x={60} y={118} width={92} height={8} rx={4} fill={C.sageDeep} />
      <rect x={76} y={84} width={14} height={34} rx={3} fill={C.orange} />
      <rect x={94} y={96} width={12} height={22} rx={3} fill={C.forest} />
      <rect x={110} y={90} width={14} height={28} rx={3} fill={C.sage} />
      {/* tokoh */}
      <g transform="translate(-6 160) scale(.9)"><BimaThinking /></g>
      {/* gelembung pikiran */}
      <circle cx={118} cy={150} r={6} fill="#fff" /><circle cx={134} cy={126} r={9} fill="#fff" />
      <g transform="translate(110 62)">
        <ellipse cx={44} cy={30} rx={46} ry={32} fill="#fff" />
        <path d="M30 34 q14 -22 28 0" stroke={C.orange} strokeWidth={4} strokeLinecap="round" fill="none" />
        <circle cx={44} cy={26} r={5} fill={C.yellow} />
        <path d="M24 44 h40" stroke={C.sage} strokeWidth={4} strokeLinecap="round" />
      </g>
      <g transform="translate(170 170)"><RaniReading /></g>
      <g transform="translate(330 196) scale(.95)"><SariForm /></g>
      <Plant x={104} y={420} s={1.15} />
      <Plant x={520} y={414} s={1.3} tone={1} />
      <Plant x={402} y={430} s={.7} tone={2} />
    </Frame>
  );
}

function Spot({ title, children, tint = C.yellowSoft, className }: { title: string; children: ReactNode; tint?: string; className?: string }) {
  return (
    <Frame className={className} vb="0 0 300 300" title={title}>
      <path d="M150 14 C236 8 290 70 286 150 C282 236 226 292 144 288 C62 284 12 224 14 144 C16 66 70 20 150 14Z" fill={tint} />
      <ellipse cx={150} cy={278} rx={104} ry={9} fill={C.sand} opacity={0.8} />
      {children}
    </Frame>
  );
}

export function WaveScene({ className }: { className?: string }) {
  return (
    <Spot className={className} title="Bima melambaikan tangan">
      <Leaf x={52} y={270} r={-20} s={.9} /><Leaf x={250} y={270} r={24} s={.8} fill={C.sageDeep} />
      <g transform="translate(40 26)"><BimaWave /></g>
    </Spot>
  );
}

export function ThinkScene({ className }: { className?: string }) {
  return (
    <Spot className={className} title="Bima sedang berpikir" tint={C.beige}>
      <circle cx={222} cy={96} r={7} fill="#fff" /><circle cx={240} cy={68} r={11} fill="#fff" />
      <g transform="translate(206 8)"><ellipse cx={42} cy={28} rx={42} ry={26} fill="#fff" /><path d="M30 34 q12 -22 24 0" stroke={C.orange} strokeWidth={4} strokeLinecap="round" fill="none" /><circle cx={42} cy={24} r={4} fill={C.yellow} /></g>
      <Leaf x={36} y={272} r={-18} s={.8} /><Leaf x={262} y={272} r={20} s={.7} fill={C.sageDeep} />
      <g transform="translate(20 22) scale(.97)"><BimaThinking /></g>
    </Spot>
  );
}

export function ReadScene({ className }: { className?: string }) {
  return (
    <Spot className={className} title="Rani sedang membaca di kursi" tint={C.yellowSoft}>
      <Plant x={252} y={268} s={.8} tone={1} />
      <g transform="translate(46 26) scale(.88)"><RaniReading /></g>
    </Spot>
  );
}

export function FormScene({ className }: { className?: string }) {
  return (
    <Spot className={className} title="Sari mengisi lembar jawaban" tint={C.beige}>
      <Leaf x={40} y={268} r={-24} s={.8} fill={C.sageDeep} /><Plant x={256} y={268} s={.7} />
      <g transform="translate(46 34) scale(.9)"><SariForm /></g>
    </Spot>
  );
}

export function RestScene({ className }: { className?: string }) {
  return (
    <Spot className={className} title="Sari beristirahat dengan secangkir teh" tint={C.yellowSoft}>
      <Plant x={48} y={266} s={.75} tone={2} /><Leaf x={256} y={270} r={22} s={.8} />
      <g transform="translate(46 30) scale(.9)"><SariRest /></g>
    </Spot>
  );
}

export function HappyScene({ className }: { className?: string }) {
  return (
    <Spot className={className} title="Rani tersenyum dengan tangan terangkat" tint={C.yellowSoft}>
      <g fill={C.orange}><circle cx={52} cy={70} r={6} /><circle cx={248} cy={60} r={5} /></g>
      <g fill={C.sage}><circle cx={78} cy={40} r={5} /><circle cx={226} cy={92} r={6} /></g>
      <g fill={C.yellow}><circle cx={36} cy={118} r={5} /><circle cx={262} cy={140} r={5} /></g>
      <Leaf x={40} y={270} r={-20} s={.8} /><Leaf x={262} y={270} r={20} s={.8} fill={C.sageDeep} />
      <g transform="translate(50 26) scale(.9)"><RaniHappy /></g>
    </Spot>
  );
}

/** Tiga tokoh berjajar, dipakai di bagian bawah halaman dan halaman kosong. */
export function Trio({ className }: { className?: string }) {
  return (
    <Frame className={className} vb="0 0 560 300" title="Rani, Bima, dan Sari berdiri berdampingan">
      <ellipse cx={280} cy={286} rx={250} ry={10} fill={C.sand} />
      <g transform="translate(10 14)"><BimaWave /></g>
      <g transform="translate(190 14)"><RaniHappy /></g>
      <g transform="translate(350 14)"><SariRest /></g>
    </Frame>
  );
}

/** Daun-daun kecil sebagai hiasan sudut. */
export function Sprig({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 120 140" aria-hidden="true">
      <Leaf x={20} y={130} r={-30} s={.7} /><Leaf x={20} y={130} r={14} s={.9} fill={C.sageDeep} /><Leaf x={20} y={130} r={50} s={.6} fill={C.forest} />
    </svg>
  );
}
