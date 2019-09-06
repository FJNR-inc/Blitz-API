

# This is a function only use in migration, when we changed the
# baseproduct meta non abstract to abstract
def update_id_on_models(
        apps, list_model_to_migrate, updated_ids, current_model):

    current_model_field_id = current_model.__name__.lower() + '_id'

    for app_name, model_name, model_field_id, field_name, is_foreign_key \
            in list_model_to_migrate:
        model = apps.get_model(app_name, model_name)

        field_name_id = field_name + '_id'

        for object_model in model.objects.all():
            if is_foreign_key:
                old_id = getattr(object_model, field_name_id, None)
                if old_id:
                    setattr(object_model, field_name_id, updated_ids[old_id])
                    object_model.save()
            else:
                field_name_m2m = getattr(model, field_name, None)
                if field_name_m2m:

                    id_value = getattr(object_model, model_field_id)
                    queryset_through_m2m = field_name_m2m.through.\
                        objects.filter(
                                **{model_name + '_id': id_value})

                    current_model_ids = []
                    for through_m2m_object in list(queryset_through_m2m):

                        current_model_ids.append(getattr(
                            through_m2m_object,
                            current_model_field_id
                            )
                        )

                    queryset_through_m2m.delete()

                    for current_model_id in current_model_ids:

                        field_name_m2m.through.objects.create(
                            **{
                                model_name + '_id': object_model.id,
                                current_model_field_id:
                                    updated_ids[current_model_id]
                            }
                        )
