import Cocoa

// MARK: - 配置
struct Config {
    let status: String      // idle, thinking, executing, waiting_input, done
    let project: String     // 项目名称
    let message: String     // 详细消息
    let terminal: String    // 终端类型
    let duration: Int       // 显示时长(秒)，0 = 一直显示

    init(from args: [String]) {
        // 参数: status project message terminal duration
        status = args.count > 1 ? args[1] : "idle"
        project = args.count > 2 ? args[2] : "Claude"
        message = args.count > 3 ? args[3] : ""
        terminal = args.count > 4 ? args[4] : "vscode"
        duration = args.count > 5 ? Int(args[5]) ?? 5 : 5
    }
}

// MARK: - 状态配置
struct StatusConfig {
    let icon: String
    let title: String
    let accentColor: NSColor      // 强调色（图标、标题）
    let glowColor: NSColor        // 发光色（边框光晕）
    let gradientStart: NSColor    // 渐变起始色
    let gradientEnd: NSColor      // 渐变结束色
}

let STATUS_CONFIG: [String: StatusConfig] = [
    "idle": StatusConfig(
        icon: "💤",
        title: "空闲",
        accentColor: NSColor(white: 0.7, alpha: 1.0),
        glowColor: NSColor(white: 0.5, alpha: 0.3),
        gradientStart: NSColor(white: 0.18, alpha: 0.92),
        gradientEnd: NSColor(white: 0.12, alpha: 0.95)
    ),
    "thinking": StatusConfig(
        icon: "🧠",
        title: "思考中",
        accentColor: NSColor(red: 1.0, green: 0.85, blue: 0.4, alpha: 1.0),
        glowColor: NSColor(red: 1.0, green: 0.8, blue: 0.2, alpha: 0.4),
        gradientStart: NSColor(red: 0.18, green: 0.14, blue: 0.08, alpha: 0.92),
        gradientEnd: NSColor(red: 0.12, green: 0.08, blue: 0.04, alpha: 0.95)
    ),
    "executing": StatusConfig(
        icon: "⚙️",
        title: "执行中",
        accentColor: NSColor(red: 0.4, green: 0.85, blue: 1.0, alpha: 1.0),
        glowColor: NSColor(red: 0.3, green: 0.7, blue: 1.0, alpha: 0.4),
        gradientStart: NSColor(red: 0.08, green: 0.14, blue: 0.18, alpha: 0.92),
        gradientEnd: NSColor(red: 0.04, green: 0.10, blue: 0.14, alpha: 0.95)
    ),
    "multi_executing": StatusConfig(
        icon: "⚡",
        title: "并行执行",
        accentColor: NSColor(red: 0.5, green: 0.9, blue: 1.0, alpha: 1.0),
        glowColor: NSColor(red: 0.4, green: 0.8, blue: 1.0, alpha: 0.5),
        gradientStart: NSColor(red: 0.10, green: 0.16, blue: 0.20, alpha: 0.92),
        gradientEnd: NSColor(red: 0.06, green: 0.12, blue: 0.16, alpha: 0.95)
    ),
    "streaming": StatusConfig(
        icon: "📝",
        title: "输出中",
        accentColor: NSColor(red: 0.5, green: 0.9, blue: 0.6, alpha: 1.0),
        glowColor: NSColor(red: 0.4, green: 0.85, blue: 0.5, alpha: 0.4),
        gradientStart: NSColor(red: 0.10, green: 0.18, blue: 0.12, alpha: 0.92),
        gradientEnd: NSColor(red: 0.06, green: 0.14, blue: 0.08, alpha: 0.95)
    ),
    "waiting_input": StatusConfig(
        icon: "⏳",
        title: "等待输入",
        accentColor: NSColor(red: 1.0, green: 0.65, blue: 0.3, alpha: 1.0),
        glowColor: NSColor(red: 1.0, green: 0.6, blue: 0.2, alpha: 0.5),
        gradientStart: NSColor(red: 0.18, green: 0.12, blue: 0.06, alpha: 0.92),
        gradientEnd: NSColor(red: 0.14, green: 0.08, blue: 0.03, alpha: 0.95)
    ),
    "tool_done": StatusConfig(
        icon: "✓",
        title: "工具完成",
        accentColor: NSColor(white: 0.6, alpha: 1.0),
        glowColor: NSColor(white: 0.4, alpha: 0.3),
        gradientStart: NSColor(white: 0.16, alpha: 0.92),
        gradientEnd: NSColor(white: 0.10, alpha: 0.95)
    ),
    "completed": StatusConfig(
        icon: "✅",
        title: "完成",
        accentColor: NSColor(red: 0.4, green: 0.9, blue: 0.5, alpha: 1.0),
        glowColor: NSColor(red: 0.3, green: 0.85, blue: 0.4, alpha: 0.4),
        gradientStart: NSColor(red: 0.08, green: 0.18, blue: 0.10, alpha: 0.92),
        gradientEnd: NSColor(red: 0.04, green: 0.14, blue: 0.06, alpha: 0.95)
    ),
    "error": StatusConfig(
        icon: "❌",
        title: "出错",
        accentColor: NSColor(red: 1.0, green: 0.4, blue: 0.4, alpha: 1.0),
        glowColor: NSColor(red: 1.0, green: 0.3, blue: 0.3, alpha: 0.5),
        gradientStart: NSColor(red: 0.18, green: 0.08, blue: 0.08, alpha: 0.92),
        gradientEnd: NSColor(red: 0.14, green: 0.04, blue: 0.04, alpha: 0.95)
    ),
    "done": StatusConfig(
        icon: "✅",
        title: "完成",
        accentColor: NSColor(red: 0.4, green: 0.9, blue: 0.5, alpha: 1.0),
        glowColor: NSColor(red: 0.3, green: 0.85, blue: 0.4, alpha: 0.4),
        gradientStart: NSColor(red: 0.08, green: 0.18, blue: 0.10, alpha: 0.92),
        gradientEnd: NSColor(red: 0.04, green: 0.14, blue: 0.06, alpha: 0.95)
    )
]

// MARK: - 渐变背景视图
class GradientBackgroundView: NSView {
    private let startColor: NSColor
    private let endColor: NSColor
    private let glowColor: NSColor

    init(frame: NSRect, startColor: NSColor, endColor: NSColor, glowColor: NSColor) {
        self.startColor = startColor
        self.endColor = endColor
        self.glowColor = glowColor
        super.init(frame: frame)
        wantsLayer = true
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)

        guard let context = NSGraphicsContext.current?.cgContext else { return }

        // 绘制圆角矩形路径
        let cornerRadius: CGFloat = 16
        let path = NSBezierPath(roundedRect: bounds, xRadius: cornerRadius, yRadius: cornerRadius)

        // 创建渐变
        let gradient = NSGradient(colors: [startColor, endColor])!
        gradient.draw(in: path, angle: 270)

        // 绘制发光边框
        context.addPath(path.cgPath)
        context.setStrokeColor(glowColor.cgColor)
        context.setLineWidth(1.5)
        context.strokePath()

        // 内发光效果（顶部高光）
        let highlightPath = NSBezierPath()
        let highlightRect = NSRect(x: 1, y: bounds.height - 1, width: bounds.width - 2, height: 1)
        highlightPath.move(to: NSPoint(x: highlightRect.minX + cornerRadius, y: highlightRect.minY))
        highlightPath.line(to: NSPoint(x: highlightRect.maxX - cornerRadius, y: highlightRect.minY))
        let highlightColor = NSColor.white.withAlphaComponent(0.08)
        highlightColor.setStroke()
        highlightPath.lineWidth = 1
        highlightPath.stroke()
    }
}

// MARK: - 悬浮窗
class FloatingWindow: NSWindow {
    private var statusLabel: NSTextField!
    private var projectLabel: NSTextField!
    private var messageLabel: NSTextField!
    private var progressIndicator: NSProgressIndicator!
    private var glowLayer: CALayer?
    private var config: Config
    private var statusConfig: StatusConfig

    init(config: Config) {
        self.config = config
        self.statusConfig = STATUS_CONFIG[config.status] ?? STATUS_CONFIG["idle"]!

        // 窗口尺寸（略微增大以适应更好的间距）
        let windowWidth: CGFloat = 300
        let windowHeight: CGFloat = 100

        // 获取屏幕尺寸，定位到右上角
        let screen = NSScreen.main!.frame
        let x = screen.width - windowWidth - 24
        let y = screen.height - windowHeight - 48

        let rect = NSRect(x: x, y: y, width: windowWidth, height: windowHeight)

        super.init(
            contentRect: rect,
            styleMask: [.borderless, .hudWindow],
            backing: .buffered,
            defer: false
        )

        setupWindow()
        setupViews()
        setupGestures()
        setupGlowAnimation()

        // 动画显示（带缩放效果）
        alphaValue = 0
        let originalFrame = self.frame
        let scaledFrame = NSRect(
            x: originalFrame.origin.x + 10,
            y: originalFrame.origin.y - 10,
            width: originalFrame.width - 20,
            height: originalFrame.height - 20
        )
        self.setFrame(scaledFrame, display: false)
        makeKeyAndOrderFront(nil)

        NSAnimationContext.runAnimationGroup { context in
            context.duration = 0.25
            context.timingFunction = CAMediaTimingFunction(name: .easeOut)
            self.animator().alphaValue = 1.0
            self.animator().setFrame(originalFrame, display: true)
        }

        // 自动关闭
        if config.duration > 0 {
            DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(config.duration)) {
                self.closeWithAnimation()
            }
        }
    }

    private func setupWindow() {
        // 窗口属性
        isOpaque = false
        backgroundColor = .clear
        hasShadow = true
        level = .floating
        collectionBehavior = [.canJoinAllSpaces, .stationary]
        isMovableByWindowBackground = true

        // 创建渐变背景视图
        let frameRect = NSRect(origin: .zero, size: self.frame.size)
        let gradientView = GradientBackgroundView(
            frame: frameRect,
            startColor: statusConfig.gradientStart,
            endColor: statusConfig.gradientEnd,
            glowColor: statusConfig.glowColor
        )

        // 设置视图阴影（通过 layer）
        gradientView.wantsLayer = true
        gradientView.layer?.shadowColor = NSColor.black.withAlphaComponent(0.5).cgColor
        gradientView.layer?.shadowOffset = NSSize(width: 0, height: -6)
        gradientView.layer?.shadowRadius = 16
        gradientView.layer?.shadowOpacity = 1.0
        gradientView.layer?.masksToBounds = false

        contentView = gradientView
    }

    private func setupViews() {
        guard let containerView = contentView else { return }

        // 状态图标和标题（带 SF Symbols 风格）
        let statusText = "\(statusConfig.icon)  \(statusConfig.title)"
        statusLabel = NSTextField(labelWithString: statusText)
        statusLabel.font = NSFont.systemFont(ofSize: 15, weight: .semibold)
        statusLabel.textColor = statusConfig.accentColor
        statusLabel.frame = NSRect(x: 20, y: 62, width: 220, height: 24)
        containerView.addSubview(statusLabel)

        // 项目名称
        projectLabel = NSTextField(labelWithString: config.project)
        projectLabel.font = NSFont.systemFont(ofSize: 13, weight: .medium)
        projectLabel.textColor = NSColor.white.withAlphaComponent(0.95)
        projectLabel.frame = NSRect(x: 20, y: 36, width: 260, height: 22)
        projectLabel.lineBreakMode = .byTruncatingMiddle
        containerView.addSubview(projectLabel)

        // 消息
        if !config.message.isEmpty {
            messageLabel = NSTextField(labelWithString: config.message)
            messageLabel.font = NSFont.systemFont(ofSize: 11, weight: .regular)
            messageLabel.textColor = NSColor.white.withAlphaComponent(0.55)
            messageLabel.frame = NSRect(x: 20, y: 14, width: 260, height: 18)
            messageLabel.lineBreakMode = .byTruncatingTail
            containerView.addSubview(messageLabel)
        }

        // 进度指示器（思考/执行时显示）
        if config.status == "thinking" || config.status == "executing" || config.status == "multi_executing" || config.status == "streaming" {
            progressIndicator = NSProgressIndicator(frame: NSRect(x: 264, y: 64, width: 18, height: 18))
            progressIndicator.style = .spinning
            progressIndicator.controlSize = .small
            progressIndicator.startAnimation(nil)
            containerView.addSubview(progressIndicator)
        }

    }

    private func setupGlowAnimation() {
        // 为等待输入状态添加呼吸发光效果
        if config.status == "waiting_input" {
            let glowLayer = CALayer()
            glowLayer.frame = contentView?.bounds ?? .zero
            glowLayer.backgroundColor = statusConfig.glowColor.withAlphaComponent(0.1).cgColor
            glowLayer.cornerRadius = 16
            contentView?.layer?.insertSublayer(glowLayer, at: 0)

            let pulseAnimation = CABasicAnimation(keyPath: "backgroundColor")
            pulseAnimation.fromValue = statusConfig.glowColor.withAlphaComponent(0.05).cgColor
            pulseAnimation.toValue = statusConfig.glowColor.withAlphaComponent(0.15).cgColor
            pulseAnimation.duration = 1.5
            pulseAnimation.autoreverses = true
            pulseAnimation.repeatCount = .infinity
            glowLayer.add(pulseAnimation, forKey: "glowPulse")
        }
    }

    private func setupGestures() {
        // 悬停效果
        let trackingArea = NSTrackingArea(
            rect: contentView?.bounds ?? .zero,
            options: [.mouseEnteredAndExited, .activeAlways, .inVisibleRect],
            owner: self,
            userInfo: nil
        )
        contentView?.addTrackingArea(trackingArea)
    }

    override func mouseEntered(with event: NSEvent) {
        NSAnimationContext.runAnimationGroup { context in
            context.duration = 0.15
            contentView?.animator().alphaValue = 0.9
        }
    }

    override func mouseExited(with event: NSEvent) {
        NSAnimationContext.runAnimationGroup { context in
            context.duration = 0.15
            contentView?.animator().alphaValue = 1.0
        }
    }

    // 直接在窗口级别处理鼠标点击
    override func mouseDown(with event: NSEvent) {
        closeWithAnimation()
    }

    private func closeWithAnimation() {
        // 直接退出，不做任何动画
        exit(0)
    }
}

// MARK: - AppDelegate
class AppDelegate: NSObject, NSApplicationDelegate {
    var window: FloatingWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let config = Config(from: CommandLine.arguments)
        window = FloatingWindow(config: config)
    }
}

// MARK: - Main
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
