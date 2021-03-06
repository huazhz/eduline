from django.shortcuts import render
from django.urls import reverse
# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from .models import UserProfile, EmailVerifyRecord
from django.db.models import Q
from django.views.generic import View
from users.forms import LoginForm, RegisterForm, ForgetForm, ModifyPwdForm
from django.contrib.auth.hashers import make_password
from utils.email_send import send_register_email
from .forms import ActiveForm, ImageUploadForm, UserInfoForm
from utils.mixin_utils import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
import json
from operation.models import UserCourse, UserFavorite, UserMessage
from organization.models import CourseOrg, Teacher
from courses.models import Course
from pure_pagination import Paginator, EmptyPage, PageNotAnInteger
from .models import Banner


# 用于实现用户注册的函数
class RegisterView(View):
    # get方法直接返回页面
    def get(self, request):
        register_form = RegisterForm()
        return render(request, "register.html", {'register_form': register_form})

    def post(self, request):
        # 类的实例化需要一个字典dict参数，而前面我们就知道request.POST是一个QueryDict，所以可以直接传入POST中的信息
        register_form = RegisterForm(request.POST)
        if register_form.is_valid():
            user_name = request.POST.get("email", "")
            if UserProfile.objects.filter(email=user_name):
                # register_form回填信息必须有，msg是信息提示
                return render(request, 'register.html', {'register_form': register_form}, {'msg': '该邮箱已被注册过了'})

            # password为前端页面name的返回值，取到用户名和密码我们就开始进行登录验证;取不到时为空。
            pass_word = request.POST.get("password", "")
            # 实例化一个user_profile对象，存入前端页面获取的值
            user_profile = UserProfile()
            user_profile.username = user_name
            user_profile.email = user_name

            # 默认激活状态为False，也就是未激活
            user_profile.is_active = False

            # 对password进行加密并保存
            user_profile.password = make_password(pass_word)
            user_profile.save()

            # 写入欢迎注册的信息
            user_message = UserMessage()
            user_message.user = user_profile.id
            user_message.message = "欢迎注册慕海学习网！"
            user_message.save()

            send_register_email(user_name, 'register')
            return render(request, "login.html", )
        else:
            return render(request, "register.html", {"register_form": register_form})


# 用于实现用户激活操作的函数
class ActiveUserView(View):
    def get(self, request, active_code):
        # 用于查询邮箱验证码是否存在
        all_record = EmailVerifyRecord.objects.filter(code=active_code)
        # 如果不为空也就是有用户
        active_form = ActiveForm(request.GET)
        if all_record:
            for record in all_record:
                # 获取到对应的邮箱
                email = record.email
                # 查找到邮箱对应的用户
                user = UserProfile.objects.get(email=email)
                user.is_active = True
                user.save()
                # 激活成功跳转到登录页面
                return render(request, "login.html", )
        else:
            return render(request, "register.html", {"msg": "您的激活链接无效", "active_form": active_form})


# 用于实现用户忘记密码（找回密码）的函数
class ForgetPwdView(View):
    def get(self, request):
        forget_form = ForgetForm()
        return render(request, "forgetpwd.html", {'forget_form': forget_form})

    def post(self, request):
        forget_form = ForgetForm(request.POST)
        if forget_form.is_valid():
            email = request.POST.get('email', '')
            # 发送找回密码的邮件
            send_register_email(email, 'forget')
            return render(request, 'send_success.html')
        else:
            return render(request, "forgetpwd.html", {'forget_form': forget_form})


# 用于实现用户重置密码的函数
class ResetView(View):
    def get(self, request, active_code):
        # 用于查询邮箱验证码是否存在
        all_record = EmailVerifyRecord.objects.filter(code=active_code)
        if all_record:
            for record in all_record:
                # 获取到对应的邮箱
                email = record.email
                # 查找到邮箱对应的用户
                return render(request, "password_reset.html", {"email": email})   # 告诉页面是哪个用户在重置密码
        else:
            return render(request, "active_fail.html")
        # 激活成功跳转到登录页面
        return render(request, "login.html")


# 用于实现用户修改密码的函数
class ModifyPwdView(View):
    def post(self, request):
        modify_form = ModifyPwdForm(request.POST)
        if modify_form.is_valid():
            pwd1 = request.POST.get("password1", '')
            pwd2 = request.POST.get("password2", '')
            email = request.POST.get("email", '')
            # 如果前后两次密码不相等，那么回填信息并返回错误提示
            if pwd1 != pwd2:
                return render(request, "password_reset.html", {"email": email, "msg": "对不起，前后密码不一致"})
            # 如果前后两次密码相等，那么进入我们的密码修改保存
            # 取出用户信息
            user = UserProfile.objects.get(email=email)
            # 随意取出一个密码并将其进行加密
            user.password = make_password(pwd1)
            # 将更新后的用户信息保存到数据库里面
            user.save()
            # 密码重置成功以后，跳转到登录页面
            return render(request, "login.html", {"msg": "恭喜您，您的密码修改成功，请登录"})
        else:
            email = request.POST.get("email", '')
            return render(request, "password_reset.html", {"email": email, "modify_form": modify_form})


# # 基于视图函数的实现用户的登录
# # 当我们配置的url被这个view处理时，将会自动传入request对象.
# def user_login(request):
#     # 前端向后端发送的请求方式有两种: get和post
#
#     # 登录提交表单时为post
#     if request.method == "POST":
#         # username，password为前端页面name的返回值，取到用户名和密码我们就开始进行登录验证;取不到时为空。
#         user_name = request.POST.get('username', '')
#         pass_word = request.POST.get('password', '')
#         # 取值成功返回user对象,失败返回null
#         user = authenticate(username=user_name, password=pass_word)
#         if user is not None:
#             # login 有两个参数：request和user。我们在请求的时候，request实际上是写进了一部分信息，然后在render的时候，这些信息也被返回前端页面从而完成用户登录。
#             login(request, user)
#             # 页面跳转至网站首页 user request也会被带回到首页，显示登录状态
#             return render(request, 'index.html')
#         else:
#             # 说明里面的值是None，再次跳转回主页面并报错
#             return render(request, "login.html", {'msg': '用户名或者密码错误！'})
#     # 获取登录页面时为get
#     elif request.method == "GET":
#         # render的作用是渲染html并返回给用户
#         # render三要素: request ，模板名称 ，一个字典用于传给前端并在页面显示
#         return render(request, "login.html", {})


#  基于类实现用户的登录，它需要继承view
class LoginView(View):
    # 不需要判断，直接调用get方法,因为是获取信息，故这里不需要验证
    def get(self, request):
        # render的作用是渲染html并返回给用户
        # render三要素: request ，模板名称 ，一个字典用于传给前端并在页面显示
        return render(request, "login.html", {})

    # 不需要判断，直接调用post方法
    def post(self, request):
        # 类的实例化需要一个字典dict参数，而前面我们就知道request.POST是一个QueryDict，所以可以直接传入POST中的username，password等信息
        login_form = LoginForm(request.POST)
        # is_valid()方法，用来判断我们所填写的字段信息是否满足我们在LoginForm中所规定的要求，验证成功则继续进行，失败就跳回login页面并重新输入信息
        if login_form.is_valid():
            # username，password为前端页面name的返回值，取到用户名和密码我们就开始进行登录验证;取不到时为空。
            user_name = request.POST.get('username', '')
            pass_word = request.POST.get('password', '')
            # 取值成功返回user对象,失败返回null
            user = authenticate(username=user_name, password=pass_word)

            if user is not None:
                if user.is_active:
                    # login 有两个参数：request和user。我们在请求的时候，request实际上是写进了一部分信息，然后在render的时候，这些信息也被返回前端页面从而完成用户登录
                    login(request, user)
                    # 页面跳转至网站首页 user request也会被带回到首页，显示登录状态
                    return HttpResponseRedirect(reverse("index"))
                else:
                    return render(request, "login.html", {'msg': '用户未激活！'})
            else:
                # 说明里面的值是None，再次跳转回主页面并报错，这里仅当用户密码出错时才返回
                return render(request, "login.html", {'msg': '用户名或者密码错误！'})
        # 所填写的字段信息不满足我们在LoginForm中所规定的要求，验证失败跳回login页面并重新输入信息
        else:
            return render(request, "login.html", {"login_form": login_form})


# 用于实现用户首页登出的函数
class LogoutView(View):
    def get(self, request):
        # 采用Django自带的logout函数来完成我们登出的功能
        logout(request)
        # 不采用之前的render，而是采用重定向返回到首页
        return HttpResponseRedirect(reverse("index"))


# 用于实现邮箱登录的函数
class CustomBackend(ModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        try:
            # 我们不希望用户存在两个，也就是说通过某个用户名和某个邮箱登录的都是指向同一用户，所以采用Q来进行并集查询
            user = UserProfile.objects.get(Q(username=username)| Q(email=username))

            # 记住不能使用password==password，因为密码都被django的后台给加密了

            # UserProfile继承的AbstractUser中有check_password这个函数
            if user.check_password(password):
                return user
        except Exception as e:
            return None


# 用户个人信息
class UserInfoView(LoginRequiredMixin , View):
    login_url = '/login/'
    redirect_field_name = 'next'

    def get(self, request):
        return render(request, "usercenter-info.html", {

        })

    def post(self, request):
        user_info_form = UserInfoForm(request.POST, instance=request.user)
        if user_info_form.is_valid():
            user_info_form.save()
            return HttpResponse('{"status":"success"}', content_type='application/json')
        else:
            return HttpResponse(json.dumps(user_info_form.errors), content_type='application/json')


# 用户头像修改
class ImageUploadView(LoginRequiredMixin, View):
    login_url = '/login/'
    redirect_field_name = 'next'

    def post(self, request):
        image_form = ImageUploadForm(request.POST, request.FILES, instance=request.user)
        if image_form.is_valid():
            image_form.save()
            return HttpResponse('{"status":"success"}', content_type='application/json')
        else:
            return HttpResponse('{"status":"fail"}', content_type='application/json')


# 用于个人中心修改密码的函数（已经登录）
class UpdatePwdView(View):
    def post(self, request):
        modify_form = ModifyPwdForm(request.POST)
        if modify_form.is_valid():
            pwd1 = request.POST.get("password1", '')
            pwd2 = request.POST.get("password2", '')
            # 如果前后两次密码不相等，那么回填信息并返回错误提示
            if pwd1 != pwd2:
                return HttpResponse('{"status":"fail", "msg":"密码不一致"}', content_type='application/json')
            # 如果前后两次密码相等，那么进入我们的密码修改保存
            # 取出用户信息
            user = request.user
            # 随意取出一个密码并将其进行加密
            user.password = make_password(pwd1)
            # 将更新后的用户信息保存到数据库里面
            user.save()
            # 密码重置成功以后，跳转到登录页面
            return HttpResponse('{"status":"success"}', content_type='application/json')
        else:
            return HttpResponse('{"status":"fail", "msg":"填写错误请检查"}', content_type='application/json')


# 用于个人中心发送邮箱验证码的函数
class SendEmailCodeView(LoginRequiredMixin, View):
    login_url = '/login/'
    redirect_field_name = 'next'

    def get(self, request):
        # 取出待发送的邮件
        email = request.GET.get("email", '')

        if UserProfile.objects.filter(email=email):
            return HttpResponse('{"email":"邮箱已经存在"}', content_type='application/json')
        send_register_email(email, "update_email")

        return HttpResponse('{"status":"success"}', content_type='application/json')


# 用于个人中心修改邮箱的函数
class UpdateEmailView(LoginRequiredMixin, View):
    login_url = '/login/'
    redirect_field_name = 'next'

    def post(self, request):
        email = request.POST.get("email", '')
        code = request.POST.get("code", '')

        existed_records = EmailVerifyRecord.objects.filter(email=email, code=code, send_type="update_email")
        if existed_records:
            # request.user.email = email
            user = request.user
            user.email = email
            user.save()
            return HttpResponse('{"status":"success"}', content_type='application/json')
        else:
            return HttpResponse('{"email":"验证码无效"}', content_type='application/json')


# 用户个人中心我的课程函数
class MyCourseView(LoginRequiredMixin, View):
    login_url = '/login/'
    redirect_field_name = 'next'

    def get(self, request):
        user_courses = UserCourse.objects.filter(user=request.user)

        return render(request, "usercenter-mycourse.html", {
            "user_courses": user_courses,

        })


# 我收藏的课程机构函数
class MyFavOrgView(LoginRequiredMixin, View):
    login_url = '/login/'
    redirect_field_name = 'next'

    def get(self, request):
        org_list = []
        fav_orgs = UserFavorite.objects.filter(user=request.user, fav_type=2)
        for fav_org in fav_orgs:
            org_id = fav_org.fav_id
            org = CourseOrg.objects.get(id=org_id)
            org_list.append(org)
        return render(request, "usercenter-fav-org.html", {
            "org_list": org_list,

        })


# 我收藏的授课讲师函数
class MyFavTeacherView(LoginRequiredMixin, View):
    login_url = '/login/'
    redirect_field_name = 'next'

    def get(self, request):
        teacher_list = []
        fav_teachers = UserFavorite.objects.filter(user=request.user, fav_type=3)
        for fav_teacher in fav_teachers:
            teacher_id = fav_teacher.fav_id
            teacher = Teacher.objects.get(id=teacher_id)
            teacher_list.append(teacher)
        return render(request, "usercenter-fav-teacher.html", {
            "teacher_list": teacher_list,

        })


# 我收藏的公开课程函数
class MyFavCourseView(LoginRequiredMixin, View):
    login_url = '/login/'
    redirect_field_name = 'next'

    def get(self, request):
        course_list = []
        fav_courses = UserFavorite.objects.filter(user=request.user, fav_type=1)
        for fav_course in fav_courses:
            course_id = fav_course.fav_id
            course = Course.objects.get(id=course_id)
            course_list.append(course)
        return render(request, "usercenter-fav-course.html", {
            "course_list": course_list,
        })


# 我的消息函数
class MyMessageView(LoginRequiredMixin, View):
    login_url = '/login/'
    redirect_field_name = 'next'

    def get(self, request):
        # 取出所有的信息
        all_messages = UserMessage.objects.filter(user=request.user.id)

        # 用户进入个人中心之后，清空未读消息
        all_unread_mesages = UserMessage.objects.filter(user=request.user.id,has_read=False)
        for unread_mesages in all_unread_mesages:
            unread_mesages.has_read = True
            unread_mesages.save()

        # 对消息进行分页,尝试获取前端get请求传递过来的page参数
        # 如果是不合法的配置参数则默认返回第一页
        try:
            page = request.GET.get('page', 1)
        except PageNotAnInteger:
            page = 1
        # 这里指从all_courses中取出来，每页显示9个
        p = Paginator(all_messages, 9, request=request)

        messages = p.page(page)

        return render(request, "usercenter-message.html", {
            "messages": messages,
        })


# 慕海学习网首页函数
class IndexView(View):
    def get(self, request):
        # 取出录播图只显示5个,并按照顺序排列
        all_banners = Banner.objects.all().order_by("index")[:5]
        # 取出轮播课程，但是只显示3个
        banner_courses = Course.objects.filter(is_banner=True)[:3]
        # 取出非轮播课程，但是只显示6个
        courses = Course.objects.filter(is_banner=False)[:6]
        # 取出课程机构，但是只显示15个
        course_orgs = CourseOrg.objects.all()[:15]
        return render(request, "index.html", {
            "all_banners": all_banners,
            "banner_courses": banner_courses,
            "courses": courses,
            "course_orgs": course_orgs,
        })


# 404页面对应的处理函数
def page_not_found(request):
    from django.shortcuts import render_to_response
    response = render_to_response("404.html", {

    })
    # 设置response的状态码
    response.status_code = 404
    return response


# 500页面对应的处理函数
def page_error(request):
    from django.shortcuts import render_to_response
    response = render_to_response("500.html", {

    })
    # 设置response的状态码
    response.status_code = 500
    return response
