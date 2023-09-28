from django.shortcuts import redirect, render
from newspaper.models import Post, Category, Tag
from django.views.generic import ListView, TemplateView
from django.utils import timezone
import datetime


class HomeView(ListView):
    model = Post
    template_name = "aznews/home.html"
    context_object_name = "posts"
    queryset = Post.objects.filter(published_at__isnull=False, status="active")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["featured_post"] = Post.objects.filter(
            published_at__isnull=False, status="active"
        ).first()
        context["featured_posts"] = Post.objects.filter(
            published_at__isnull=False, status="active"
        )[1:4]

        context["recent_posts"] = Post.objects.filter(
            published_at__isnull=False, status="active"
        ).order_by("-published_at")[:7]

        one_week_ago = timezone.now() - datetime.timedelta(days=7)
        context["weekly_top_posts"] = Post.objects.filter(
            published_at__isnull=False,
            status="active",
            published_at__gte=one_week_ago,  # greater than or equal
        ).order_by("-published_at", "-views_count")[:7]

        return context


class AboutView(TemplateView):
    template_name = "aznews/about.html"


class PostListView(ListView):
    model = Post
    template_name = "aznews/list/list.html"
    context_object_name = "posts"
    queryset = Post.objects.filter(
        published_at__isnull=False, status="active"
    ).order_by("-published_at")
    paginate_by = 1


class PostByCategoryView(ListView):
    model = Post
    template_name = "aznews/list/list.html"
    context_object_name = "posts"
    paginate_by = 1

    def get_queryset(self):
        return Post.objects.filter(
            published_at__isnull=False,
            status="active",
            category__id=self.kwargs.get("category_id"),
        ).order_by("-published_at")


class PostByTagView(ListView):
    model = Post
    template_name = "aznews/list/list.html"
    context_object_name = "posts"
    paginate_by = 1

    def get_queryset(self):
        return Post.objects.filter(
            published_at__isnull=False,
            status="active",
            tag__id=self.kwargs.get("tag_id"),
        ).order_by("-published_at")


from django.views.generic import View, DetailView
from newspaper.forms import ContactForm
from django.contrib import messages


class ContactView(View):
    template_name = "aznews/contact.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Your message has been submitted. We will contact you soon."
            )
            return redirect("contact")
        else:
            messages.error(
                request,
                "Cannot submit your message. Please check your form and try again.",
            )
            return render(
                request,
                self.template_name,
                {"form": form},
            )


class PostDetailView(DetailView):
    model = Post
    template_name = "aznews/detail/detail.html"
    context_object_name = "post"

    def get_queryset(self):
        query = super().get_queryset()
        query = query.filter(published_at__isnull=False, status="active")
        return query

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        obj.views_count += 1
        obj.save()

        # 4 => 1, 2, ,3  =>  3, 2, 1
        context["previous_post"] = (
            Post.objects.filter(
                published_at__isnull=False, status="active", id__lt=obj.id
            )
            .order_by("-id")
            .first()
        )

        # 4 => 5, 6, 7, 8, 9 , 10 ....
        context["next_post"] = (
            Post.objects.filter(
                published_at__isnull=False, status="active", id__gt=obj.id
            )
            .order_by("id")
            .first()
        )

        return context


from newspaper.forms import CommentForm


class CommentView(View):
    def post(self, request, *args, **kwargs):
        form = CommentForm(request.POST)
        post_id = request.POST["post"]
        if form.is_valid():
            form.save()
            return redirect("post-detail", post_id)

        post = Post.objects.get(pk=post_id)
        return render(
            request,
            "aznews/detail/detail.html",
            {"post": post, "form": form},
        )


from django.http import JsonResponse
from newspaper.forms import NewsletterForm


class NewsletterView(View):
    def post(self, request):
        is_ajax = request.headers.get("x-requested-with")
        if is_ajax == "XMLHttpRequest": # ajax request
            form = NewsletterForm(request.POST)
            if form.is_valid():
                form.save()
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Successfully subscribed to the newsletter.",
                    },
                    status=201,
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Cannot subscribe to the newsletter.",
                    },
                    status=400,
                )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Cannot process. Must be an AJAX XMLHttpRequest",
                },
                status=400,
            )
        

from django.core.paginator import Paginator, PageNotAnInteger
from django.db.models import Q


class PostSearchView(View):
    template_name = "aznews/list/list.html"
    
    def get(self, request, *args, **kwargs):
        query = request.GET["query"]
        post_list = Post.objects.filter(
            (Q(title__icontains=query) | Q(content__icontains=query))
            & Q(status="active")
            & Q(published_at__isnull=False)
        ).order_by("-published_at")

        # pagination start

        page = request.GET.get("page", 1) #2
        paginate_by = 3
        paginator = Paginator(post_list, paginate_by)
        try:
            posts = paginator.page(page)
        except PageNotAnInteger:
            posts= paginator.page(1)

        #pagination end
        return render(
            request,
            self.template_name,
            {"page_obj": posts, "query": query},
        )