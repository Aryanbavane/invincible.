import {
  Activity,
  CircleHelp,
  Droplet,
  HeartPulse,
  Siren,
  UserRound,
  X,
  Check,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const icons: Record<string, LucideIcon> = {
  YES: Check,
  NO: X,
  HELP: CircleHelp,
  WATER: Droplet,
  PAIN: HeartPulse,
  COME_HERE: UserRound,
  EMERGENCY: Siren,
};

export default function CommandGlyph({ command }: { command?: string }) {
  const Icon = icons[command ?? ""] ?? Activity;
  return <Icon aria-hidden="true" className="command-glyph" size={28} strokeWidth={1.75} />;
}