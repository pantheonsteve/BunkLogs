/** Suggested parent group types per child type (bunk → unit → division). */
export const PARENT_TYPES_FOR = {
  bunk: ['unit', 'division'],
  unit: ['division'],
  classroom: ['cohort', 'division'],
  cohort: ['division'],
  specialty: ['unit', 'division'],
  custom: ['division', 'unit'],
};

export function parentTypesFor(childType) {
  return PARENT_TYPES_FOR[childType] || [];
}

export function canHaveParent(childType) {
  return parentTypesFor(childType).length > 0;
}
