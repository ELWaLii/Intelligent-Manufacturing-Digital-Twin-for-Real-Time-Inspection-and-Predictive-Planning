from sqlalchemy.orm import Session
from planning_request import PlanningRequestModel

def simulate_and_save_request(db: Session, target_productivity: float, max_allowed_overtime: float, current_machine_stage: int):
    idle_impact = 0.0
    if current_machine_stage >= 2:
        idle_impact = 0.35 
    if target_productivity > 0.95:
        status = "REJECTED"
        required_incentive = 0.0
        required_overtime = 0.0
        idle_impact = 1.0
        justification = "القرار مرفوض: استهداف إنتاجية أعلى من 95% غير عملي بالمرة ولا يتوافق مع معدلات الأعطال والصيانة التاريخية للمصنع."
    else:
        # حساب الحوافز والـ Overtime المطلوبين ديناميكياً
        required_incentive = (target_productivity * 150) + (idle_impact * 200)
        required_overtime = (target_productivity * 4000) * (1 + idle_impact)
        
        status = "APPROVED"
        justification = "القرار مقبول تشغيلياً: تم حساب الميزانية المطلوبة وساعات العمل الإضافية للوصول للمستهدف بنجاح."
        
        # مراجعة القيود (Constraints)
        if required_overtime > max_allowed_overtime:
            status = "WARNING"
            justification = f"تحذير: ساعات العمل الإضافية المطلوبة ({round(required_overtime)} ساعة) تتخطى السقف المسموح به. يرجى تعديل القيود أو زيادة العمالة."
            
        if current_machine_stage == 3:
            status = "REJECTED"
            justification = "القرار مرفوض قطعيًا: الماكينة الحالية في حالة انهيار تام (Stage 3). خطة زيادة الإنتاج مستحيلة قبل عمل صيانة وتغيير الأداة."

    db_record = PlanningRequestModel(
        target_productivity=target_productivity,
        max_allowed_overtime=max_allowed_overtime,
        current_machine_stage=current_machine_stage,
        decision_status=status,
        required_incentive=round(required_incentive, 2),
        required_overtime=round(required_overtime, 2),
        predicted_idle_impact=round(idle_impact, 2),
        justification=justification
    )
    
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    
    return db_record