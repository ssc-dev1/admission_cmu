from odoo import api, fields, models, tools


class FacultyStaffLoad(models.Model):
    _name = "faculty.staff.load"
    _description = "Faculty Staff Load"
    _auto = False

    faculty_staff_id = fields.Many2one('odoocms.faculty.staff', string='Faculty Staff')
    institute_id = fields.Many2one('odoocms.institute', string='Institute/Faculty')
    department_id = fields.Many2one('odoocms.department', string='Department')
    program_id = fields.Many2one('odoocms.program', string='Program')
    type = fields.Selection(string='Type', related='faculty_staff_id.employee_id.employment_nature')
    credit_hours = fields.Float('Credit Hours')
    code = fields.Char('Code')
    title = fields.Char('Title')
    class_id = fields.Many2one('odoocms.class', string='Class')
    term_id = fields.Many2one('odoocms.academic.term', string='Academic term')
    strength = fields.Integer('Strength')

    section = fields.Char('Section')
    class_faculty_id = fields.Many2one('odoocms.institute', string='Class Faculty')
    class_dept_id = fields.Many2one('odoocms.department', string='Class Dept')
    company_id = fields.Many2one('res.company','Company')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'faculty_staff_load')
        self.env.cr.execute("""
            create or replace view faculty_staff_load as (
                    SELECT
                    cf.id,
                    cf.faculty_staff_id,
                    fs.institute as institute_id,
                    fs.department_id as department_id,
                    b.program_id as program_id,                    
                    (CASE WHEN cp.parent_id is null then cf.credits ELSE 0 END) as credit_hours,                    
                    c.code,
                    c.section_name as section,
                    c.institute_id as class_faculty_id,
                    c.department_id as class_dept_id,
                    c.term_id,
                    c.name as title,
                    c.id as class_id,
                    c.company_id as company_id,
                    COALESCE(rc.count, 0) as strength
                    FROM odoocms_class_faculty cf
                    JOIN odoocms_class c ON cf.class_id = c.id
                    JOIN odoocms_class_primary cp on c.primary_class_id = cp.id
                    JOIN odoocms_batch b on cp.batch_id = b.id                    
                    JOIN odoocms_faculty_staff fs ON cf.faculty_staff_id = fs.id
                    LEFT JOIN
                    (
                        SELECT class_id, COUNT(*) as count
                        FROM odoocms_student_course_component
                        GROUP BY class_id
                    ) rc ON c.id = rc.class_id
                )
                    """)

                #  cf.credits as credit_hours,
