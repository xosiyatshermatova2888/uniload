import type { FieldDef, FormValues } from "@/components/common/entity-form-dialog"
import type { Schemas } from "@/lib/api/client"

type Teacher = Schemas["TeacherOut"]

export function teacherFields(t: (k: string) => string): FieldDef[] {
  return [
    { name: "last_name", label: t("teachers.lastName"), required: true },
    { name: "first_name", label: t("teachers.firstName"), required: true },
    { name: "middle_name", label: t("teachers.middleName") },
    { name: "employee_no", label: t("teachers.employeeNo"), required: true },
    { name: "academic_degree", label: t("teachers.degree"), type: "select", required: true,
      options: (["none", "phd", "dsc"] as const).map((d) => ({ value: d, label: t(`teachers.degrees.${d}`) })) },
    { name: "academic_title", label: t("teachers.titleField"), type: "select", required: true,
      options: (["none", "docent", "professor", "senior_researcher"] as const).map((d) => ({ value: d, label: t(`teachers.titles.${d}`) })) },
    { name: "email", label: t("users.email") },
    { name: "phone", label: t("users.phone") },
    { name: "is_active", label: t("form.active"), type: "checkbox" },
  ]
}

export function teacherInitial(item?: Teacher): FormValues {
  return item ? {
    last_name: item.last_name, first_name: item.first_name, middle_name: item.middle_name ?? "", employee_no: item.employee_no,
    academic_degree: item.academic_degree, academic_title: item.academic_title, email: item.email ?? "", phone: item.phone ?? "",
    is_active: item.is_active,
  } : { academic_degree: "none", academic_title: "none", is_active: true }
}
