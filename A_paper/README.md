# 武汉大学本科毕业设计（论文）LaTeX 模板

本项目为武汉大学本科毕业设计（论文）LaTeX 模板。本模板在 whu-thesis 2019 版的基础上进行修改以符合 2021 级（2025届）国家网络安全学院的要求。

## 样例展示

![pic1](.assets/pic1.png)

![pic2](.assets/pic2.png)

![pic3](.assets/pic3.png)

![pic4](.assets/pic4.png)

![pic5](.assets/pic5.png)


完整样例请查看 demo.pdf。

## 注意事项

1. 本模板需使用 XeLaTeX 进行编译，支持本地及在线编译。
2. 请注意本模板**未经任何学校相关部门审核**，使用前请仔细斟酌。如有出入请以官方 Word 模板为准。
3. 模板仅供学习交流使用，任何由使用本模板引起的问题与 whu-thesis 及本人无关。

## 本地编译

项目内已提供 `Makefile` 与本地 TinyTeX 环境，直接运行：

```bash
make pdf
```

生成文件为 `main.pdf`。

为兼容 `whu-bachelor-style.cls` 对 `Times New Roman` 的依赖，本地构建会通过 `fonts/` 与 `fonts.conf` 加载项目内字体映射，不需要修改模板类文件。

## 致谢

武汉大学毕业论文 LaTeX 模板：[whu-thesis](https://github.com/whutug/whu-thesis)
