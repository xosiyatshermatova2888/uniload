"use client"

import { useQuery } from "@tanstack/react-query"
import { useMemo } from "react"

import { api, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"

/** Ma’lumotnomalar uchun umumiy so‘rovlar (kesh kalitlari bir joyda — invalidatsiya oson). */
export const refKeys = {
  faculties: ["faculties"] as const,
  departments: ["departments"] as const,
  programs: ["programs"] as const,
  subjects: ["subjects"] as const,
  lessonTypes: ["lesson-types"] as const,
  curricula: ["curricula"] as const,
  teachers: ["teachers"] as const,
  teacherCatalog: ["teachers", "catalog"] as const,
}

export function useFaculties() {
  const { can } = useAuth()
  return useQuery({ queryKey: refKeys.faculties, queryFn: () => unwrap(api.GET("/api/v1/faculties")), enabled: can("org.view") })
}

export function useDepartments() {
  const { can } = useAuth()
  return useQuery({ queryKey: refKeys.departments, queryFn: () => unwrap(api.GET("/api/v1/departments")), enabled: can("org.view") })
}

export function usePrograms() {
  const { can } = useAuth()
  return useQuery({ queryKey: refKeys.programs, queryFn: () => unwrap(api.GET("/api/v1/programs")), enabled: can("programs.view") })
}

export function useSubjects() {
  const { can } = useAuth()
  return useQuery({ queryKey: refKeys.subjects, queryFn: () => unwrap(api.GET("/api/v1/subjects")), enabled: can("subjects.view") })
}

export function useLessonTypes() {
  const { can } = useAuth()
  return useQuery({ queryKey: refKeys.lessonTypes, queryFn: () => unwrap(api.GET("/api/v1/lesson-types")), enabled: can("curriculum.view") })
}

export function useCurricula() {
  const { can } = useAuth()
  return useQuery({ queryKey: refKeys.curricula, queryFn: () => unwrap(api.GET("/api/v1/curricula")), enabled: can("curriculum.view") })
}

export function useTeachers() {
  const { can } = useAuth()
  return useQuery({ queryKey: refKeys.teachers, queryFn: () => unwrap(api.GET("/api/v1/teachers")), enabled: can("teachers.view") })
}

export function useTeacherCatalog() {
  const { can } = useAuth()
  return useQuery({
    queryKey: refKeys.teacherCatalog,
    queryFn: () => unwrap(api.GET("/api/v1/teachers/catalog")),
    enabled: can("teachers.view"),
    staleTime: Infinity,
  })
}

/** id → nom xaritasi (jadvallarda bog‘liq yozuv nomini ko‘rsatish uchun). */
export function useNameMap<T extends { id: string }>(items: T[] | undefined, label: (item: T) => string) {
  return useMemo(() => new Map((items ?? []).map((i) => [i.id, label(i)])), [items, label])
}

export type Curriculum = Schemas["CurriculumOut"]

export function curriculumLabel(c: Curriculum, programs: Map<string, string>, t: (k: string) => string) {
  return `${programs.get(c.education_program_id) ?? "—"} · ${c.admission_year} · ${t(`curricula.forms.${c.education_form}`)} · v${c.version}`
}
