import wx
import os
from threading import Thread
# import wx.lib.pubsub.pub
from pubsub import pub
from bs4 import BeautifulSoup
import html2text
from lxml import etree
import requests
import webbrowser
import json
import wx.html
import re
import win32api
headers = {
    # 'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1",
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
    'Connection': 'keep-alive'
}


class TestThread:
    def __init__(self, login_url, dir_path, is_choice):
        # 线程实例化时立即启动
        # self.thread = thread
        self.login_url = login_url
        self.dir_path = dir_path
        self.is_choice = is_choice
        # Thread.__init__(self)
        # self.start()
        # print(login_url, dir_path)
        self.run()

    def run(self):
        match_path = re.findall('\\$', self.dir_path)
        if not match_path:           # 判断是输入的文件存放路径的末尾是否加反斜杠
            self.dir_path = self.dir_path + '/'
        # 线程执行的代码
        # for i in range(11):
        with open('./static/cookie.json', 'r') as f:      # 读取配置的cookie文件
            self.cookies = json.load(f)
            print(self.cookies)

        r = requests.get(self.login_url, cookies=self.cookies, headers=headers).content
        content = etree.HTML(r)
        article_list = content.xpath('//div[ @class="catalog_view"]/a/@onclick')
        if not article_list:  # 恶心的是，有的时候链接是在div下的，一般是a标签下例如：https://gitbook.cn/gitchat/column/5b6d05446b66e3442a2bfa7b
            article_list = content.xpath('//div[ @class="catalog_view"]/div/@onclick')

        self.chapter_title = content.xpath('//div[@class="catalog_items_head"]/a/text()')[0]  # 获取课程名称
        self.dir_path_title = self.dir_path + self.chapter_title  # 生成课程的根目录
        if not os.path.exists(self.dir_path_title):
            os.makedirs(self.dir_path_title)
        # u1 = self.login_url.split('/')[-1]  # 拼接每个章节url
        for u in article_list:
            # u2 = re.findall('clickOnTopic\(\'(.+)\'', u)[0]
            url_info = re.findall(r"clickOnTopic\(\'(?P<blog>.+)\',\'(?P<directory>.+)\',\'(?P<is_free>.+)\',\'(?P<is_done>.+)\'\)", u)[0]
            a_url = 'https://gitbook.cn/gitchat/column/' + url_info[1] + '/topic/' + url_info[0]
            print(a_url)
            wx.CallAfter(pub.sendMessage, "update", message=a_url + '\n')
            is_free = url_info[2]
            is_done = url_info[3]
            if is_done:
                if self.is_choice == 0:       # 说明下载pdf
                    self.get_pdf(a_url)
                elif self.is_choice == 1:        # 说明下载md
                    self.get_md(a_url)
                elif self.is_choice == 2:             # 说明同时下载md和pdf
                    self.get_pdf(a_url)
                    # wx.CallAfter(pub.sendMessage, "update", message='开始下载markdown格式...' + '\n')
                    self.get_md(a_url)
            else:
                is_done_message = '*** %s ***文章正在写作中...'
                wx.CallAfter(pub.sendMessage, "update", message=is_done_message + '\n')

        wx.CallAfter(pub.sendMessage, "update", message='***下载完毕，如果章节不全的话，请添加cookie以及购买相关课程***')

    def get_md(self, a_url):
        """获取到博客文章的内容部分的html代码"""
        self.dir_path_md = self.dir_path + self.chapter_title + '/' + 'markdown格式'
        if not os.path.exists(self.dir_path_md):
            os.makedirs(self.dir_path_md)

        r = requests.get(a_url, cookies=self.cookies, headers=headers).text
        # print(r)

        soup = BeautifulSoup(r, 'lxml')
        content = soup.find_all('div', class_='topicContainer')
        if content:
            content = content[0]
            html_code = str(content.contents[0])

            title = str(soup.title.string).replace(' ', '').replace('|', '-')
            # print(title)
            title_message = '*** %s ***markdown格式开始下载' % title
            wx.CallAfter(pub.sendMessage, "update", message=title_message + '\n')
            self.change_md(html_code, title)

        else:
            wx.CallAfter(pub.sendMessage, "update", message='!!!此章节付费章节，请购买后在下载...' + '\n')

    # html = open("article.html").read().encode('utf8')

    def change_md(self, txt, title):
        """html代码转markdown"""
        ht = html2text.HTML2Text()
        htmlpage = txt
        text = html2text.html2text(htmlpage).encode('utf8')
        # print(text)
        try:
            if os.path.exists(self.dir_path_md + '/' + title + '.md'):       # 判断文件是否存在
                success_already = '*** %s ***已存在、markdown格式下载完毕' % title
                wx.CallAfter(pub.sendMessage, "update", message=success_already + '\n')
            else:
                with open(self.dir_path_md + '/' + title + '.md', 'wb') as f:
                    f.write(text)
                    success_message = '*** %s ***、markdown下载完毕' % title
                    wx.CallAfter(pub.sendMessage, "update", message=success_message + '\n')
        except Exception as e:
            print(e)
            error_down = '***%s下载出错了' % title
            wx.CallAfter(pub.sendMessage, "update", message=error_down + '\n')

    def get_pdf(self, a_url):
        """下载pdf格式操作"""
        self.dir_path_pdf = self.dir_path + self.chapter_title + '/' + 'pdf格式'
        if not os.path.exists(self.dir_path_pdf):
            os.makedirs(self.dir_path_pdf)
        r = requests.get(a_url, cookies=self.cookies, headers=headers).content

        content = etree.HTML(r)
        title = content.xpath('/html/head/title/text()')[0]        # 获取章节标题
        title = title.replace(' ', '').replace('|', '-')
        # print(chapter_title)

        src_content = content.xpath('//div[@class="column_topic_view"]/script/text()')
        if src_content:
            href = re.findall('href = \'(.+)\'', src_content[0])[0]               # 解析到pdf的下载路径url
            print(href)
            if os.path.exists(self.dir_path_pdf + '/' + title + '.pdf'):     # 判断文件是否存在
                success_already = '*** %s ***PDF格式、已存在、下载完毕' % title
                wx.CallAfter(pub.sendMessage, "update", message=success_already + '\n')
            else:
                pdf_content = requests.get(href, cookies=self.cookies, headers=headers).content  # request 文件pdf的data
                with open(self.dir_path_pdf + '/' + title + '.pdf', 'wb') as f:
                    f.write(pdf_content)
                success_message = '*** %s ***PDF格式、下载完毕' % title
                wx.CallAfter(pub.sendMessage, "update", message=success_message + '\n')
        else:
            error_down = '***%s ***不支持PDF下载或者下载出错了或者购买后在下载！' % title
            wx.CallAfter(pub.sendMessage, "update", message=error_down + '\n')


class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title)
        self.SetBackgroundColour('white')
        # self.SetBackgroundStyle()
        self.icon = wx.Icon(name="./static/logo.ico", type=wx.BITMAP_TYPE_ICO)
        self.SetIcon(self.icon)

        # 创建窗口栏
        # self.statusbar = self.CreateStatusBar()  # 创建位于窗口的底部的状态栏

        # 设置菜单
        filemenu = wx.Menu()

        # wx.ID_ABOUT和wx.ID_EXIT是wxWidgets提供的标准ID
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&关于我",
                                    " Information about this program")  # (ID, 项目名称, 状态栏信息)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        filemenu.AppendSeparator()
        menuExit = filemenu.Append(wx.ID_EXIT, "E&xit",
                                   " Terminate the program")  # (ID, 项目名称, 状态栏信息)
        self.Bind(wx.EVT_MENU, self.exit, menuExit)

        study_menu = wx.Menu()            # 创建软件使用教程的菜单栏
        study_use = study_menu.Append(wx.ID_NEW, '软件使用教程', 'use study')
        self.Bind(wx.EVT_MENU, self.study_use, study_use)
        study_menu.AppendSeparator()
        add_cookie = study_menu.Append(-1, '添加cookie', 'add cookie')
        self.Bind(wx.EVT_MENU, self.edit_cookie, add_cookie)
        # 创建顶部菜单栏
        menuBar = wx.MenuBar()
        menuBar.Append(study_menu, "&使用攻略")  # 在菜单栏中添加filemenu菜单
        menuBar.Append(filemenu, "&关于我")  # 在菜单栏中添加filemenu菜单
        self.SetMenuBar(menuBar)  # 在frame中添加菜单栏

        # 设置events

        # 创建一些Sizer
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.GridBagSizer(hgap=5, vgap=5)    # 行和列的间距是5像素
        hSizer = wx.BoxSizer(wx.VERTICAL)

        self.url = wx.StaticText(self, label='课程链接：', pos=(20, 30))
        # self.Bind(wx.EVT_MOTION, self.show_status, self.url)
        self.url_blog = wx.TextCtrl(self, pos=(100, 20), size=(420, -1))  # style=wx.TE_RICH
        # self.url_blog.SetDefaultStyle(wx.TextAttr(wx.RED))
        grid.Add(self.url, pos=(0, 0))    # 加入GridBagSizer
        grid.Add(self.url_blog, pos=(0, 1))    # 加入GridBagSizer
        self.clear_button = wx.Button(self, -1, "清除")
        grid.Add(self.clear_button, pos=(0, 2))
        self.Bind(wx.EVT_BUTTON, self.clear_url)
        # self.Bind(wx.EVT_ENTER_WINDOW, self.show_status, self.clear_button)

        # 向GridBagSizer中填充空白的空间
        # grid.Add((10, 40), pos=(2, 0))

        # self.button = wx.Button(self, label='Save', pos=(200, 325))
        # self.Bind(wx.EVT_BUTTON, self.OnClick, self.button)

        self.lblname = wx.StaticText(self, label='下载路径：', pos=(20, 20))
        grid.Add(self.lblname, pos=(2, 0))
        self.dir_path = wx.TextCtrl(self, pos=(10, 10), size=(420, -1), )
        grid.Add(self.dir_path, pos=(2, 1))
        self.liulan_button = wx.Button(self, -1, "浏览")
        grid.Add(self.liulan_button, pos=(2, 2))
        self.Bind(wx.EVT_BUTTON, self.OnOpen, self.liulan_button)

        # 选择下载的格式
        self.name_md = wx.StaticText(self, label='下载格式:', pos=(20, 20))
        grid.Add(self.name_md, pos=(3, 0))
        self.is_md_list = ['pdf', 'markdown', 'pdf和markdown']
        self.is_md = wx.ComboBox(self, value='请选择下载格式', pos=wx.DefaultPosition, size=(120, 35), choices=self.is_md_list,
                                 style=wx.CB_DROPDOWN)
        grid.Add(self.is_md, pos=(3, 1))

        # # 向GridBagSizer中填充空白的空间
        grid.Add((10, 20), pos=(4, 0))

        self.download = wx.Button(self, label='download', pos=(10, 15))        # 总的下载按钮
        # grid.Add(self.download, pos=(4, 2), span=(1, 3))
        # self.download.Position()
        self.Bind(wx.EVT_BUTTON, self.down, self.download)

        self.d_info = wx.StaticText(self, label='下载输出信息：', pos=(10, 10))
        font = wx.Font(12,  wx.ROMAN, wx.NORMAL, wx.FONTWEIGHT_BOLD)          # 设置字体大小
        self.d_info.SetFont(font)
        self.d_info.SetForegroundColour('red')           # 设置StaticText部件的文本颜色
        # grid.Add(self.d_info, pos=(6, 0))
        self.logger = wx.TextCtrl(self, pos=(100, 20), size=(600, 300), style=wx.TE_MULTILINE | wx.TE_READONLY,
                                  value='下载输入信息...\n'
                                  )
        # grid.Add(self.logger, pos=(7, 0), span=(1, 3), flag=wx.BOTTOM, border=5)
        hSizer.Add(grid, 0, wx.ALL, 5)
        # hSizer.Add(self.download)
        mainSizer.Add(hSizer, 0, wx.ALL, 5)
        mainSizer.Add(self.download, 0, wx.CENTER)
        # mainSizer.Add(self.is_md, 0, wx.Left)
        mainSizer.Add((20, 20))                # 添加上下空白间隔
        mainSizer.Add(self.d_info, 0, wx.Left)
        mainSizer.Add((20, 5))  # 添加上下空白间隔
        mainSizer.Add(self.logger, 0, wx.CENTER)
        # 可以把SetSizer()和sizer.Fit()合并成一条SetSizerAndFit()语句
        self.SetSizerAndFit(mainSizer)
        pub.subscribe(self.down_message, "update")  # 获取到子线程中发来的数据
        self.Show(True)

    def OnAbout(self, e):
        """关于我"""
        # 创建一个带"OK"按钮的对话框。wx.OK是wxWidgets提供的标准ID
        # dlg = wx.MessageDialog(self, "开发者：教主\n一个python开发者&人工智能&爬虫钟爱者...",
        #                        "关于开发者我...", wx.OK)  # 语法是(self, 内容, 标题, ID)
        # # dlg.WebSite = ("http://www.pythonlibrary.org", "My Home Page")
        # dlg.ShowModal()  # 显示对话框
        # dlg.Destroy()  # 当结束之后关闭对话框
        aboutDlg = AboutDlg(None)
        aboutDlg.Show()

    def OnOpen(self, e):
        """ 打开文件操作 """
        # wx.FileDialog语法：(self, parent, message, defaultDir, defaultFile,
        #                    wildcard, style, pos)
        dlg = wx.DirDialog(self, "Choose a file", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            dir_path = dlg.GetPath()
            self.dir_path.SetValue(dir_path)
            # self.filename = dlg.GetFilename()
            # self.dirname = dlg.GetDirectory()
            # f = open(os.path.join(self.dirname, self.filename), 'r')  # 暂时只读
            # self.control.SetValue(f.read())
            # f.close()
        dlg.Destroy()

    def clear_url(self, event):
        """清理博客链接函数"""
        self.url_blog.SetValue('')

    def down(self, event):
        """下载博客操作"""
        # print('jgg')
        url = self.url_blog.GetValue()        # 获取课程主页链接
        # print('url %s' % url)
        dir_path = self.dir_path.GetValue()    # 获取存放文件的文件夹路径

        is_choice = self.is_md.GetSelection()      # =-1为其他 =0 为pdf下载器，=1位markdown下载器 =2 为两种格式同时下载
        # print(type(is_choice))
        # print('dir_path %s' % dir_path)
        if url and dir_path:             # 判断路径以及博客链接是否为空
            if is_choice == -1:
                alerm = wx.MessageDialog(self, "填写信息有误，下载格式未选择...", u"error!!!")
                alerm.ShowModal()
            else:
                self.logger.SetValue('')  # 清空下载日志区
                t = Thread(target=TestThread, args=(url, dir_path, is_choice))
                t.setDaemon(True)
                t.start()
        else:
            self.verify_down()
        # t.join()
        # event.GetEventObject().Disable()
        # x = TestThread()
        # event.GetEventObject().Disable()  #

    def down_message(self, message):
        self.logger.AppendText(message)

    def verify_down(self):
        dlg = wx.MessageDialog(self, "填写信息有误，请检查路径以及博客链接填写是否正确...", u"error!!!", wx.YES_NO | wx.ICON_QUESTION)
        # if dlg.ShowModal() == wx.ID_YES:
        #     self.Close(True)
        dlg.ShowModal()
        dlg.Destroy()

    def exit(self, e):
        is_quit = wx.MessageDialog(None, "要退出gitchat下载器吗？", "exit", wx.YES_NO | wx.ICON_QUESTION)
        # is_quit.ShowModal()  # 显示对话框
        if is_quit.ShowModal() == wx.ID_YES:
            self.Close()
        else:
            pass
        is_quit.Destroy()  # 当结束之后关闭对话框

    # def show_status(self, e):
    #     self.statusbar.SetStatusText('25252')

    def study_use(self, e):
        webbrowser.open('https://gitee.com/pekachu/gitchat_download')

    def edit_cookie(self, e):
        path = './static/cookie.json'
        win32api.ShellExecute(0, 'open', 'notepad.exe', path, '', 1)


class AboutDlg(wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, wx.ID_ANY, title="关于我...", size=(400, 400))
        self.icon = wx.Icon(name="./static/logo.ico", type=wx.BITMAP_TYPE_ICO)
        self.SetIcon(self.icon)
        html = wxHTML(self)

        html.SetPage(
            ''
            "<h3>关于开发者我...</h3>"
            "<p><b>开发者：西园公子 </b></p>"
            "<p><b>一个python&人工智能&爬虫钟爱者...</b></p>"
            "<p>软件开源，欢迎star</p>"
            '<p><b><a href="https://github.com/jz46/gitchat_download">软件项目github地址</a></b></p>'
        )


class wxHTML(wx.html.HtmlWindow):
    def OnLinkClicked(self, link):
        webbrowser.open(link.GetHref())


app = wx.App(False)
# frame = wx.Frame(None, title="Demo with Notebook")
frame = MainWindow(None, title='gitchat下载器')
# nb = wx.Notebook(frame)
# #
# # nb.AddPage(ExamplePanel(nb), "Absolute Positioning")
# # nb.AddPage(ExamplePanel(nb), "Page Two")
# # nb.AddPage(ExamplePanel(nb), "Page Three")

# frame.Show()
app.MainLoop()
