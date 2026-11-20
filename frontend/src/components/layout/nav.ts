import {
  Activity,
  AudioLines,
  ClipboardList,
  FilePlus2,
  FileText,
  Gauge,
  History,
  Layers,
  ScanFace,
  Settings,
  Stethoscope,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

export const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Overview",
    items: [{ to: "/", label: "Dashboard", icon: Gauge, end: true }],
  },
  {
    label: "Analysis",
    items: [
      { to: "/analysis/new", label: "New analysis", icon: FilePlus2 },
      { to: "/analysis/face", label: "Face analysis", icon: ScanFace },
      { to: "/analysis/motion", label: "Motion analysis", icon: Activity },
      { to: "/analysis/voice", label: "Voice analysis", icon: AudioLines },
      { to: "/analysis/combined", label: "Multimodal", icon: Layers },
    ],
  },
  {
    label: "Records",
    items: [
      { to: "/history", label: "Analysis history", icon: History },
      { to: "/reports", label: "Reports", icon: FileText },
      { to: "/audit", label: "Audit activity", icon: ClipboardList },
    ],
  },
  {
    label: "System",
    items: [
      { to: "/diagnostics", label: "Diagnostics", icon: Stethoscope },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];
