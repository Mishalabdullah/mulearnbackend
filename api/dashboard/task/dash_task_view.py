import uuid

from openpyxl import Workbook
from rest_framework.views import APIView
from db.task import TaskList, Channel, TaskType, Level, InterestGroup
from db.organization import Organization
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils, ImportCSV
from .dash_task_serializer import TaskListSerializer
from db.user import User


class TaskApi(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        task_serializer = TaskList.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(task_serializer, request, ["id",
                                                                                           "hashtag",
                                                                                           "title",
                                                                                           "karma",
                                                                                           "channel",
                                                                                           "type",
                                                                                           "active",
                                                                                           "variable_karma",
                                                                                           "usage_count",
                                                                                           "created_by",
                                                                                           "created_at"])
        task_serializer_data = TaskListSerializer(paginated_queryset.get('queryset'), many=True).data

        return CustomResponse().paginated_response(data=task_serializer_data,
                                                   pagination=paginated_queryset.get('pagination'))

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request):  # create
        user_id = JWTUtils.fetch_user_id(request)
        task_data = TaskList.objects.create(
            id=uuid.uuid4(),
            hashtag=request.data.get('hashtag'),
            title=request.data.get('title'),
            description=request.data.get('description'),
            karma=request.data.get('karma'),
            channel_id=request.data.get('channel_id'),
            type_id=request.data.get('type_id'),
            active=request.data.get('active'),
            variable_karma=request.data.get('variable_karma'),
            usage_count=request.data.get('usage_count'),
            level_id=request.data.get('level_id'),
            ig_id=request.data.get('ig_id'),
            updated_by_id=user_id,
            updated_at=DateTimeUtils.get_current_utc_time(),
            created_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time())
        serializer = TaskListSerializer(task_data)
        return CustomResponse(response={"taskList": serializer.data}).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request, pk):  # edit
        user_id = JWTUtils.fetch_user_id(request)
        taskData = TaskList.objects.filter(id=pk).first()
        fields_to_update = ["hashtag",
                            "title",
                            "karma",
                            "active",
                            "variable_karma",
                            "usage_count"]
        for field in fields_to_update:
            if field in request.data:
                setattr(taskData, field, request.data[field])
        taskData.updated_by = User.objects.filter(id=user_id).first()
        taskData.updated_at = DateTimeUtils.get_current_utc_time()
        taskData.save()
        serializer = TaskListSerializer(taskData)
        print(serializer.data)
        return CustomResponse(
            response={"taskList": serializer.data}
        ).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def patch(self, request, pk):  # delete
        user_id = JWTUtils.fetch_user_id(request)
        taskData = TaskList.objects.filter(id=pk).first()
        taskData.active = False
        taskData.updated_by = User.objects.filter(id=user_id).first()
        taskData.updated_at = DateTimeUtils.get_current_utc_time()
        taskData.save()
        serializer = TaskListSerializer(taskData)
        return CustomResponse(
            response={"taskList": serializer.data}
        ).get_success_response()


class TaskListCSV(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def get(self, request):
        task_serializer = TaskList.objects.all()
        task_serializer_data = TaskListSerializer(task_serializer, many=True).data

        return CommonUtils.generate_csv(task_serializer_data, 'Task List')


class ImportTaskListCSV(APIView):
    authentication_classes = [CustomizePermission]
    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request):
        try:
            file_obj = request.FILES['task_list']
        except KeyError:
            return CustomResponse(general_message={'File not found.'}).get_failure_response()

        excel_data = ImportCSV.read_excel_file(file_obj)
        if not excel_data:
            return CustomResponse(general_message={'Empty csv file.'}).get_failure_response()

        temp_headers = ['hashtag', 'title', 'description', 'karma', 'usage_count', 'variable_karma', 'level', 'channel',
                        'type', 'ig', 'org']
        first_entry = excel_data[0]
        for key in temp_headers:
            if key not in first_entry:
                return CustomResponse(general_message={f'{key} does not exist in the file.'}).get_failure_response()

        valid_rows = []
        error_rows = []

        for row in excel_data[1:]:
            hashtag = row.get('hashtag')
            title = row.get('title')
            description = row.get('description')
            karma = row.get('karma')
            usage_count = row.get('usage_count')
            variable_karma = row.get('variable_karma')
            level = row.pop('level')
            channel = row.pop('channel')
            task_type = row.pop('type')
            ig = row.pop('ig')
            org = row.pop('org')

            channel_obj = Channel.objects.filter(name=channel).first()
            task_type_obj = TaskType.objects.filter(title=task_type).first()
            level_obj = Level.objects.filter(name=level).first() if level is not None else None
            ig_obj = InterestGroup.objects.filter(name=ig).first() if ig is not None else None
            org_obj = Organization.objects.filter(code=org).first() if org is not None else None

            if TaskList.objects.filter(hashtag=hashtag).exists():
                row['error'] = f"Hashtag already exists: {hashtag}"
                error_rows.append(row)
            elif not channel_obj:
                row['error'] = f"Invalid channel ID: {channel}"
                error_rows.append(row)
            elif not task_type_obj:
                row['error'] = f"Invalid task type ID: {task_type}"
                error_rows.append(row)
            elif level and not level_obj:
                row['error'] = f"Invalid level ID: {level}"
                error_rows.append(row)
            elif ig and not ig_obj:
                row['error'] = f"Invalid interest group ID: {ig}"
                error_rows.append(row)
            elif org and not org_obj:
                row['error'] = f"Invalid organization ID: {org}"
                error_rows.append(row)
            else:
                user_id = 1
                row['id'] = uuid.uuid4()
                row['updated_by_id'] = user_id
                row['updated_at'] = str(DateTimeUtils.get_current_utc_time())
                row['created_by_id'] = user_id
                row['created_at'] = str(DateTimeUtils.get_current_utc_time())
                row['active'] = True
                row['channel_id'] = channel_obj.id if channel_obj else None
                row['type_id'] = task_type_obj.id if task_type_obj else None
                row['level_id'] = level_obj.id if level_obj else None
                row['ig_id'] = ig_obj.id if ig_obj else None
                row['org_id'] = org_obj.id if ig_obj else None
                TaskList.objects.create(**row)
                print(row)
                valid_rows.append(row)

        return CustomResponse(response={"Success": valid_rows, "Failed": error_rows}).get_success_response()
            # workbook = Workbook()
            # valid_sheet = workbook.active
            # valid_headers = list(valid_rows[0].keys())
            # valid_sheet.append(valid_headers)
            #
            # error_sheet = workbook.create_sheet(title='Invalid Rows')
            # error_headers = list(error_rows[0].keys())
            # error_sheet.append(error_headers)

            # for row in valid_rows:
            #     valid_sheet.append([row.get(header, '') for header in valid_headers])
            #
            # for row in error_rows:
            #     error_sheet.append([row.get(header, '') for header in error_headers])


class TaskGetAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def get(self, request, pk):
        task_serializer = TaskList.objects.get(id=pk)
        serializer = TaskListSerializer(task_serializer)
        return CustomResponse(response={"Task": serializer.data}).get_success_response()