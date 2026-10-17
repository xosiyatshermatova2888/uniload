import {
  BookOpen,
  Building2,
  CalendarRange,
  CheckCircle2,
  ClipboardList,
  FileBarChart,
  GraduationCap,
  LayoutDashboard,
  Landmark,
  Library,
  Link2,
  Network,
  Settings,
  Share2,
  Users,
  UsersRound,
  type LucideIcon,
} from "lucide-react"

import type { MessageKey } from "@/i18n"

/** Joriy ishlab chiqish bosqichi: `phase <= CURRENT_PHASE` bo‘lgan bo‘limlar ochiq. */
export const CURRENT_PHASE = 2

export interface NavItem {
  key: MessageKey
  href: string
  icon: LucideIcon
  /** Qaysi bosqichda ishga tushadi. 1 — tayyor. */
  phase: number
  permission?: string
}

export interface NavSection {
  title: MessageKey
  items: NavItem[]
}

/** Sidebar — docs/07-frontend.md bo‘yicha 15 bo‘lim. */
export const tenantNav: NavSection[] = [
  {
    title: "nav.sectionMain",
    items: [
      { key: "nav.dashboard", href: "/dashboard", icon: LayoutDashboard, phase: 1, permission: "dashboard.view" },
      { key: "nav.academicYears", href: "/academic-years", icon: CalendarRange, phase: 1, permission: "academic_year.view" },
    ],
  },
  {
    title: "nav.sectionReference",
    items: [
      { key: "nav.faculties", href: "/faculties", icon: Landmark, phase: 2, permission: "org.view" },
      { key: "nav.departments", href: "/departments", icon: Building2, phase: 2, permission: "org.view" },
      { key: "nav.programs", href: "/programs", icon: GraduationCap, phase: 2, permission: "programs.view" },
      { key: "nav.curricula", href: "/curricula", icon: ClipboardList, phase: 2, permission: "curriculum.view" },
      { key: "nav.subjects", href: "/subjects", icon: BookOpen, phase: 2, permission: "subjects.view" },
      { key: "nav.groups", href: "/groups", icon: UsersRound, phase: 2, permission: "groups.view" },
      { key: "nav.teachers", href: "/teachers", icon: Users, phase: 2, permission: "teachers.view" },
    ],
  },
  {
    title: "nav.sectionWorkload",
    items: [
      { key: "nav.workloadCalc", href: "/workload/calculation", icon: Library, phase: 3, permission: "workload.view" },
      { key: "nav.workloadDist", href: "/workload/distribution", icon: Share2, phase: 3, permission: "workload.distribute" },
      { key: "nav.approvals", href: "/approvals", icon: CheckCircle2, phase: 4, permission: "approval.department" },
      { key: "nav.reports", href: "/reports", icon: FileBarChart, phase: 4, permission: "reports.view" },
    ],
  },
  {
    title: "nav.sectionSystem",
    items: [
      { key: "nav.espos", href: "/integrations/espos", icon: Link2, phase: 5, permission: "integrations.view" },
      { key: "nav.settings", href: "/settings", icon: Settings, phase: 1, permission: "settings.view" },
    ],
  },
]

export const platformNav: NavSection[] = [
  {
    title: "nav.platform",
    items: [{ key: "nav.universities", href: "/platform/universities", icon: Network, phase: 1 }],
  },
]

export const settingsTabs: { key: MessageKey; href: string; permission: string }[] = [
  { key: "settings.university", href: "/settings/university", permission: "settings.view" },
  { key: "settings.users", href: "/settings/users", permission: "users.manage" },
  { key: "settings.roles", href: "/settings/roles", permission: "users.manage" },
  { key: "settings.norms", href: "/settings/norms", permission: "teachers.view" },
  { key: "settings.lessonTypes", href: "/settings/lesson-types", permission: "curriculum.view" },
]
