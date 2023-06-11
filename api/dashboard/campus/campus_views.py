from rest_framework.views import APIView

from db.organization import UserOrganizationLink
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import serializers
from django.db.models import Sum, Case, When, IntegerField

class StudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.CAMPUS_LEAD])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(user_id=user_id,
                                                            org__org_type=OrganizationType.COLLEGE.value).first()
        user_org_links = UserOrganizationLink.objects.filter(org_id=user_org_link.org_id)
        paginated_queryset = CommonUtils.get_paginated_queryset(user_org_links, request, ['user__first_name'])
        serializer = serializers.UserOrgSerializer(paginated_queryset.get('queryset'), many=True).data
        sorted_persons = sorted(serializer, key=lambda x: x['karma'], reverse=True)
        for i, person in enumerate(sorted_persons):
            person['rank'] = i + 1

        return CustomResponse(response={"data": sorted_persons,
                                        'pagination': paginated_queryset.get('pagination')}).get_success_response()


class StudentDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.CAMPUS_LEAD])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(user_id=user_id,
                                                            org__org_type=OrganizationType.COLLEGE.value).first()
        user_org_links = UserOrganizationLink.objects.filter(
            org_id=user_org_link.org_id)

        serializer = serializers.UserOrgSerializer(user_org_links, many=True)
        return CommonUtils.generate_csv(serializer.data, 'Campus Details')


class CampusDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.CAMPUS_LEAD])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = UserOrganizationLink.objects.filter(
            user_id=user_id, org__org_type=OrganizationType.COLLEGE.value).first()
        serializer = serializers.CollegeSerializer(user_org_link, many=False)
        return CustomResponse(response=serializer.data).get_success_response()